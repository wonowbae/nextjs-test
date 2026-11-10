import "dotenv/config";
import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "../src/generated/prisma/client";

const db = new PrismaClient({ adapter: new PrismaPg({ connectionString: process.env.DATABASE_URL! }) });
const names = ["Alex Kim", "Morgan Lee", "Taylor Park", "Jordan Choi", "Casey Han", "Robin Jung", "Jamie Seo", "Drew Yoon", "Skyler Lim", "Avery Song"];
const roles = ["ADMIN", "MANAGER", "MEMBER"] as const;
const statuses = ["ACTIVE", "INVITED", "SUSPENDED"] as const;
async function main() {
  for (let i = 0; i < 250; i++) {
    const id = String(i + 1).padStart(3, "0");
    await db.user.upsert({
      where: { email: `user${id}@example.test` },
      update: {},
      create: {
        name: `${names[i % names.length]} ${id}`,
        email: `user${id}@example.test`,
        role: roles[i % roles.length],
        status: statuses[(Math.floor(i / 3) + i) % statuses.length],
        createdAt: new Date(Date.UTC(2025, 0, 1 + i)),
      },
    });
  }
  console.log("Seeded 250 demo users (idempotent)");
}
main().finally(() => db.$disconnect());
