import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Note of Accountability",
    short_name: "NoA",
    description: "Notes, tasks and focus timers for staying disciplined.",
    start_url: "/",
    display: "standalone",
    background_color: "#050407",
    theme_color: "#6d5ef0",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      {
        src: "/icons/icon-maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
