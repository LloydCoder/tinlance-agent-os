from tinlance_agent_os.catalog_evaluation import evaluate
def test_evaluation_is_explicit():
 e=evaluate("CAT-001",{"selection_accuracy":1},{"selection_accuracy":1})
 assert e.passed
