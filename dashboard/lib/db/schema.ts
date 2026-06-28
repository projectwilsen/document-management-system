import { pgTable, uuid, varchar, timestamp, integer, date } from "drizzle-orm/pg-core"

export const organizations = pgTable("organizations", {
  id: uuid("id").primaryKey().$defaultFn(() => crypto.randomUUID()),
  name: varchar("name", { length: 255 }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).$defaultFn(() => new Date()).notNull(),
})

export const users = pgTable("users", {
  id: uuid("id").primaryKey().$defaultFn(() => crypto.randomUUID()),
  organizationId: uuid("organization_id").notNull().references(() => organizations.id),
  email: varchar("email", { length: 255 }).notNull().unique(),
  passwordHash: varchar("password_hash", { length: 255 }).notNull(),
  role: varchar("role", { length: 50 }).notNull().$defaultFn(() => "owner")
    .$type<"owner" | "member">(),
  createdAt: timestamp("created_at", { withTimezone: true }).$defaultFn(() => new Date()).notNull(),
})

export const subscriptions = pgTable("subscriptions", {
  id: uuid("id").primaryKey().$defaultFn(() => crypto.randomUUID()),
  organizationId: uuid("organization_id").notNull().references(() => organizations.id),
  plan: varchar("plan", { length: 50 }).notNull().$defaultFn(() => "free")
    .$type<"free" | "starter" | "pro">(),
  docLimit: integer("doc_limit"),
  periodStart: date("period_start").notNull(),
  periodEnd: date("period_end").notNull(),
})

export const usageLogs = pgTable("usage_logs", {
  id: uuid("id").primaryKey().$defaultFn(() => crypto.randomUUID()),
  organizationId: uuid("organization_id").notNull().references(() => organizations.id),
  userId: uuid("user_id").notNull().references(() => users.id),
  filesProcessed: integer("files_processed").notNull(),
  syncedAt: timestamp("synced_at", { withTimezone: true }).$defaultFn(() => new Date()).notNull(),
})
