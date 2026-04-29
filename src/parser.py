def load_testcase(base_path, case_name):
    import json
    import os

    case_dir = os.path.join(base_path, "examples", case_name)

    with open(os.path.join(case_dir, "streams.json")) as f:
        streams = json.load(f)["streams"]

    with open(os.path.join(case_dir, "topology.json")) as f:
        topology = json.load(f)["topology"]

    with open(os.path.join(case_dir, "routes.json")) as f:
        routes = json.load(f)["routes"]

    return streams, topology, routes


def load_all_testcases(base_path):
    import os

    examples_dir = os.path.join(base_path, "examples")
    case_names = sorted(
        d for d in os.listdir(examples_dir)
        if os.path.isdir(os.path.join(examples_dir, d)) and d.startswith("test_case")
    )
    return {name: load_testcase(base_path, name) for name in case_names}