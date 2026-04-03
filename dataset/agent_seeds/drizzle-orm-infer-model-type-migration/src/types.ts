import type { InferModel } from "drizzle-orm";
import { users } from "./schema";

type User = InferModel<typeof users>;
type NewUser = InferModel<typeof users, "insert">;

export type { User, NewUser };
