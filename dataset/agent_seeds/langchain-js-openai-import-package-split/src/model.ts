import { ChatOpenAI } from "langchain/chat_models/openai";

export const llm = new ChatOpenAI({
  model: "gpt-4o-mini",
  temperature: 0,
});
