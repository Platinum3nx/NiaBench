import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

export async function generate(prompt: string): Promise<string> {
  const response = await client.completions.create({
    model: "claude-2.1",
    max_tokens_to_sample: 256,
    prompt,
  });
  return response.completion;
}
