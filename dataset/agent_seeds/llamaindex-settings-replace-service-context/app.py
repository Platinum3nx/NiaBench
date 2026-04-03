from llama_index.core import ServiceContext

service_context = ServiceContext.from_defaults(llm=llm, embed_model=embed_model)
