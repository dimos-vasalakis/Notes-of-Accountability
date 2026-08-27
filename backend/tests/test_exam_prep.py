import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam_prep import ExamConfig, ExamSubject, StudySession

STUDENT = {
    "email": "student@example.com",
    "password": "supersecret1",
    "is_student": True,
}
NON_STUDENT = {"email": "civilian@example.com", "password": "supersecret1"}

EXAM_DATE = date(2027, 6, 1)


@pytest.fixture
async def seeded_track(db_session: AsyncSession) -> None:
    """The test schema is created from metadata, so seed the track by hand."""
    db_session.add(
        ExamConfig(
            track="group_d",
            academic_year="2026-2027",
            exam_date=EXAM_DATE,
            is_active=True,
        )
    )
    for order, (code, weight) in enumerate(
        [("neoelliniki", 1.0), ("mathimatika", 1.3), ("aepp", 1.3), ("aoth", 1.0)], 1
    ):
        db_session.add(
            ExamSubject(
                track="group_d",
                code=code,
                name_el=code,
                name_en=code,
                weight_coefficient=weight,
                display_order=order,
                is_active=True,
            )
        )
    await db_session.commit()


async def test_signup_with_student_mode_sets_track(client: AsyncClient) -> None:
    response = await client.post("/api/auth/signup", json=STUDENT)

    assert response.status_code == 201
    body = response.json()
    assert body["is_student"] is True
    assert body["exam_track"] == "group_d"


async def test_signup_without_student_mode_has_no_track(client: AsyncClient) -> None:
    body = (await client.post("/api/auth/signup", json=NON_STUDENT)).json()

    assert body["is_student"] is False
    assert body["exam_track"] is None


async def test_non_student_is_forbidden(client: AsyncClient, seeded_track: None) -> None:
    await client.post("/api/auth/signup", json=NON_STUDENT)

    assert (await client.get("/api/exam-prep/config")).status_code == 403
    assert (await client.get("/api/exam-prep/subjects")).status_code == 403
    assert (await client.get("/api/exam-prep/allocation")).status_code == 403


async def test_opting_in_later_unlocks_exam_prep(
    client: AsyncClient, seeded_track: None
) -> None:
    await client.post("/api/auth/signup", json=NON_STUDENT)
    assert (await client.get("/api/exam-prep/config")).status_code == 403

    patched = await client.patch("/api/auth/me", json={"is_student": True})

    assert patched.status_code == 200
    assert patched.json()["exam_track"] == "group_d"
    assert (await client.get("/api/exam-prep/config")).status_code == 200


async def test_config_reports_days_remaining(
    client: AsyncClient, seeded_track: None
) -> None:
    await client.post("/api/auth/signup", json=STUDENT)

    body = (await client.get("/api/exam-prep/config")).json()

    assert body["exam_date"] == EXAM_DATE.isoformat()
    assert body["days_remaining"] == (EXAM_DATE - datetime.now(UTC).date()).days


async def test_subjects_are_ordered(client: AsyncClient, seeded_track: None) -> None:
    await client.post("/api/auth/signup", json=STUDENT)

    subjects = (await client.get("/api/exam-prep/subjects")).json()

    assert [s["code"] for s in subjects] == [
        "neoelliniki",
        "mathimatika",
        "aepp",
        "aoth",
    ]


async def test_log_study_session(client: AsyncClient, seeded_track: None) -> None:
    await client.post("/api/auth/signup", json=STUDENT)

    response = await client.post(
        "/api/exam-prep/study-sessions",
        json={"subject_code": "aepp", "duration_seconds": 1500},
    )

    assert response.status_code == 201
    assert response.json()["subject_code"] == "aepp"
    assert response.json()["source"] == "focus_timer"

    assert len((await client.get("/api/exam-prep/study-sessions")).json()) == 1


async def test_unknown_subject_is_rejected(
    client: AsyncClient, seeded_track: None
) -> None:
    await client.post("/api/auth/signup", json=STUDENT)

    response = await client.post(
        "/api/exam-prep/study-sessions",
        json={"subject_code": "astrophysics", "duration_seconds": 1500},
    )

    assert response.status_code == 404


async def test_non_positive_duration_is_rejected(
    client: AsyncClient, seeded_track: None
) -> None:
    await client.post("/api/auth/signup", json=STUDENT)

    response = await client.post(
        "/api/exam-prep/study-sessions", json={"duration_seconds": 0}
    )

    assert response.status_code == 422


async def test_allocation_is_all_planned_before_any_study(
    client: AsyncClient, seeded_track: None
) -> None:
    await client.post("/api/auth/signup", json=STUDENT)

    allocation = (await client.get("/api/exam-prep/allocation")).json()

    assert len(allocation) == 4
    assert sum(row["planned_share"] for row in allocation) == pytest.approx(1.0)
    assert all(row["actual_seconds"] == 0 for row in allocation)
    assert all(row["actual_share"] == 0.0 for row in allocation)


async def test_allocation_reflects_logged_time(
    client: AsyncClient, seeded_track: None
) -> None:
    await client.post("/api/auth/signup", json=STUDENT)
    # All time on one subject: it should read as heavily over-allocated.
    await client.post(
        "/api/exam-prep/study-sessions",
        json={"subject_code": "aepp", "duration_seconds": 3600},
    )

    allocation = {
        row["subject_code"]: row
        for row in (await client.get("/api/exam-prep/allocation")).json()
    }

    aepp = allocation["aepp"]
    assert aepp["actual_seconds"] == 3600
    assert aepp["actual_share"] == pytest.approx(1.0)
    assert aepp["delta"] > 0
    assert allocation["mathimatika"]["delta"] < 0


async def test_allocation_ignores_sessions_outside_the_window(
    client: AsyncClient, db_session: AsyncSession, seeded_track: None
) -> None:
    signup = await client.post("/api/auth/signup", json=STUDENT)
    owner_id = uuid.UUID(signup.json()["id"])
    # Inserted directly: the API deliberately refuses to backdate this far.
    db_session.add(
        StudySession(
            owner_id=owner_id,
            subject_code="aepp",
            duration_seconds=3600,
            occurred_at=datetime.now(UTC) - timedelta(days=40),
        )
    )
    await db_session.commit()

    weekly = (await client.get("/api/exam-prep/allocation?window=week")).json()

    assert all(row["actual_seconds"] == 0 for row in weekly)


async def test_future_session_is_rejected(
    client: AsyncClient, seeded_track: None
) -> None:
    """A future timestamp would mark the user active forever."""
    await client.post("/api/auth/signup", json=STUDENT)
    future = (datetime.now(UTC) + timedelta(days=365)).isoformat()

    response = await client.post(
        "/api/exam-prep/study-sessions",
        json={"duration_seconds": 1500, "occurred_at": future},
    )

    assert response.status_code == 422


async def test_heavily_backdated_session_is_rejected(
    client: AsyncClient, seeded_track: None
) -> None:
    """Backdating is how a fake multi-day streak would be minted."""
    await client.post("/api/auth/signup", json=STUDENT)
    old = (datetime.now(UTC) - timedelta(days=30)).isoformat()

    response = await client.post(
        "/api/exam-prep/study-sessions",
        json={"duration_seconds": 1500, "occurred_at": old},
    )

    assert response.status_code == 422


async def test_unsupported_exam_track_is_rejected(client: AsyncClient) -> None:
    """An unknown or empty track would leave the account with no subjects."""
    await client.post("/api/auth/signup", json=NON_STUDENT)

    for bad in ["", "group_z", "x" * 40]:
        response = await client.patch(
            "/api/auth/me", json={"is_student": True, "exam_track": bad}
        )
        assert response.status_code == 422, bad


async def test_study_sessions_are_per_user(
    client: AsyncClient, seeded_track: None
) -> None:
    await client.post("/api/auth/signup", json=STUDENT)
    await client.post(
        "/api/exam-prep/study-sessions",
        json={"subject_code": "aepp", "duration_seconds": 1500},
    )
    await client.post("/api/auth/logout")

    await client.post(
        "/api/auth/signup",
        json={**NON_STUDENT, "is_student": True},
    )

    assert (await client.get("/api/exam-prep/study-sessions")).json() == []


async def test_null_is_student_is_rejected_not_a_500(client: AsyncClient) -> None:
    """is_student is NOT NULL; an explicit null must not reach the DB."""
    await client.post("/api/auth/signup", json=NON_STUDENT)

    response = await client.patch("/api/auth/me", json={"is_student": None})

    assert response.status_code == 422


async def test_non_student_can_log_an_untagged_session(
    client: AsyncClient, seeded_track: None
) -> None:
    """A focus session counts toward everyone's streak, not just students'."""
    await client.post("/api/auth/signup", json=NON_STUDENT)

    response = await client.post(
        "/api/exam-prep/study-sessions", json={"duration_seconds": 1500}
    )

    assert response.status_code == 201
    assert (await client.get("/api/pods/me/streak")).json()["current_streak"] == 1


async def test_non_student_cannot_tag_a_subject(
    client: AsyncClient, seeded_track: None
) -> None:
    await client.post("/api/auth/signup", json=NON_STUDENT)

    response = await client.post(
        "/api/exam-prep/study-sessions",
        json={"subject_code": "aepp", "duration_seconds": 1500},
    )

    assert response.status_code == 404


async def test_subject_from_another_track_is_rejected(
    client: AsyncClient, db_session: AsyncSession, seeded_track: None
) -> None:
    """Otherwise the time is accepted, then silently dropped from allocation."""
    db_session.add(
        ExamSubject(
            track="group_c",
            code="latin",
            name_el="Λατινικά",
            name_en="Latin",
            weight_coefficient=1.0,
            display_order=1,
            is_active=True,
        )
    )
    await db_session.commit()
    await client.post("/api/auth/signup", json=STUDENT)

    response = await client.post(
        "/api/exam-prep/study-sessions",
        json={"subject_code": "latin", "duration_seconds": 1500},
    )

    assert response.status_code == 404
