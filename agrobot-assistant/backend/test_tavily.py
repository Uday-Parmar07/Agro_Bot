from tavily import TavilyClient

tavily = TavilyClient(api_key="")

response = tavily.search(
    query="government schemes for farmers Madhya Pradesh",
    
    search_depth="advanced",

    include_domains=[
        "gov.in",
        "nic.in",
        "agricoop.gov.in",
        "farmer.gov.in",
        "mp.gov.in"
    ],

    max_results=5
)

for result in response['results']:
    print(result['title'])
    print(result['url'])
    print(result['content'])
    print()