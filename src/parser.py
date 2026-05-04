import json
import os
    
REQUIRED_FILES = ("streams.json", "topology.json", "routes.json")

def load_testcase(case_dir):

    with open(os.path.join(case_dir, "streams.json")) as f:
        streams = json.load(f)["streams"]

    with open(os.path.join(case_dir, "topology.json")) as f:
        topology = json.load(f)["topology"]

    with open(os.path.join(case_dir, "routes.json")) as f:
        routes = json.load(f)["routes"]

    return streams, topology, routes


def is_testcase_dir(path):
    return (
        os.path.isdir(path)
        and all(os.path.isfile(os.path.join(path, name)) for name in REQUIRED_FILES)
    )


def load_all_testcases(base_path):
    
    testcases_root = os.path.join(base_path, "test_cases")
    testcases = {}

    for root, dirs, files in os.walk(testcases_root):
        if is_testcase_dir(root):
            case_name = os.path.relpath(root, testcases_root)
            testcases[case_name] = load_testcase(root)

    return dict(sorted(testcases.items()))