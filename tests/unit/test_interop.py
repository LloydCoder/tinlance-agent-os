from tinlance_agent_os.interop import from_a2a_card,from_mcp_metadata
def test_protocol_adapters_remain_descriptive():
 assert from_a2a_card({"version":"1","url":"u","skills":["research"]}).protocol=="a2a"
 assert from_mcp_metadata({"version":"2026-07-28","endpoint":"e","tools":["search"]}).capabilities==("search",)
