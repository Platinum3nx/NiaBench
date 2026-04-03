export async function runChain(chain: any, question: string) {
  return chain.call({ input: question });
}
