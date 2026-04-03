import NextAuth from "next-auth";

export default NextAuth({
  session: { jwt: true },
  providers: [],
});
