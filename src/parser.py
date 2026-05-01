def load_testcase(case_dir):
    import json
    import os

    with open(os.path.join(case_dir, "streams.json")) as f:
        streams = json.load(f)["streams"]

    with open(os.path.join(case_dir, "topology.json")) as f:
        topology = json.load(f)["topology"]

    with open(os.path.join(case_dir, "routes.json")) as f:
        routes = json.load(f)["routes"]

    return streams, topology, routes


def _find_testcases(root_dir, prefix=None):
    import os

    if not os.path.isdir(root_dir):
        return []

    case_names = sorted(
        d for d in os.listdir(root_dir)
        if os.path.isdir(os.path.join(root_dir, d)) and d.startswith("test_case")
    )
    if prefix:
        return [
            (os.path.join(root_dir, name), f"{prefix}/{name}")
            for name in case_names
        ]
    return [(os.path.join(root_dir, name), name) for name in case_names]


def load_all_testcases(base_path):
    import os

    examples_dir = os.path.join(base_path, "examples")
    case_paths = []
    case_paths.extend(_find_testcases(examples_dir, "examples"))
    case_paths.extend(_find_testcases(os.path.join(examples_dir, "examples_simulator", "generated", "baseline"), "baseline"))
    case_paths.extend(_find_testcases(os.path.join(examples_dir, "examples_simulator", "generated", "heavy"), "heavy"))

    return {name: load_testcase(path) for path, name in case_paths}