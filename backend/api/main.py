from fastapi import FastAPI
from elasticsearch import AsyncElasticsearch
from dotenv import load_dotenv
import os
import typing

load_dotenv(".env.dev")

print(os.getenv("ES_HOST"))
print(os.getenv("ES_API_KEY"))

app = FastAPI()
es_host = os.getenv("ES_HOST")
es_api_key = os.getenv("ES_API_KEY")
es_cert_path = os.getenv("ES_CERT_PATH")

es = AsyncElasticsearch(
    es_host,
    api_key=es_api_key,
    verify_certs=True,
    ca_certs=es_cert_path,
)


@app.get("/health")
async def health():
    try:
        cluster_health = await es.cluster.health()
        return {"status": "healthy", "cluster": cluster_health}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/doc")
async def get_doc():
    if not await es.indices.exists(index="test_index"):
        await es.indices.create(index="test_index")

    await es.index(index="test_index",
                   id="test_doc_id",
                   document={
                       "foo": "foo",
                       "bar": "bar"
                   })

    return await es.get(index="test_index", id="test_doc_id")


@app.get('/')
async def root():
    return {"message": "hello world"}
