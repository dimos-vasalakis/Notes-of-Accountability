"""Edit the Panhellenic exam subjects, their weight coefficients, and the exam date.

These values change every year by ministry decision (ΦΕΚ), so they live in the
database rather than in code. Edit the SUBJECTS / EXAM_DATE constants below and
re-run; the script upserts by `code` / `track`, so running it twice is a no-op
and it never duplicates or orphans existing rows.

    python -m scripts.seed_exam_config

Run from the `backend/` directory with the app's virtualenv active.
"""

import asyncio
from datetime import date

from sqlmodel import select

from app.core.db import async_session_maker
from app.models.exam_prep import ExamConfig, ExamSubject

# --- EDIT THESE EACH EXAM SEASON ------------------------------------------
TRACK = "group_d"  # Ομάδα Προσανατολισμού Οικονομίας & Πληροφορικής
ACADEMIC_YEAR = "2026-2027"

# The first day of the Panhellenic exams. PLACEHOLDER — verify against the
# official ministry announcement for the current year.
EXAM_DATE = date(2027, 6, 1)

# (code, name_el, name_en, weight_coefficient, display_order)
# PLACEHOLDER coefficients — verify against the current-year ΦΕΚ. They differ
# per scientific field (επιστημονικό πεδίο) and change between years.
SUBJECTS = [
    ("neoelliniki", "Νεοελληνική Γλώσσα και Λογοτεχνία", "Modern Greek Language and Literature", 1.0, 1),
    ("mathimatika", "Μαθηματικά", "Mathematics", 1.3, 2),
    ("aepp", "Ανάπτυξη Εφαρμογών σε Προγραμματιστικό Περιβάλλον", "Application Development in a Programming Environment", 1.3, 3),
    ("aoth", "Αρχές Οικονομικής Θεωρίας", "Principles of Economic Theory", 1.0, 4),
]
# --------------------------------------------------------------------------


async def seed() -> None:
    async with async_session_maker() as db:
        seeded_codes = set()
        for code, name_el, name_en, weight, order in SUBJECTS:
            subject = await db.scalar(select(ExamSubject).where(ExamSubject.code == code))
            if subject is None:
                subject = ExamSubject(code=code)
                db.add(subject)
            subject.track = TRACK
            subject.name_el = name_el
            subject.name_en = name_en
            subject.weight_coefficient = weight
            subject.display_order = order
            subject.is_active = True
            seeded_codes.add(code)

        # Deactivate rather than delete subjects dropped from SUBJECTS, so
        # historical study sessions tagged with them stay readable.
        existing = await db.scalars(select(ExamSubject).where(ExamSubject.track == TRACK))
        for subject in existing:
            if subject.code not in seeded_codes:
                subject.is_active = False

        config = await db.scalar(select(ExamConfig).where(ExamConfig.track == TRACK))
        if config is None:
            config = ExamConfig(track=TRACK)
            db.add(config)
        config.academic_year = ACADEMIC_YEAR
        config.exam_date = EXAM_DATE
        config.is_active = True

        await db.commit()

    print(f"Seeded {len(SUBJECTS)} subjects and the exam config for track '{TRACK}'.")


if __name__ == "__main__":
    asyncio.run(seed())
