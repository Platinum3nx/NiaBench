import OpenAI from "openai";

const client = new OpenAI();

export async function generate(input: string) {
  return client.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [{ role: "user", content: input }],
    temperature: 0,
  });
}
