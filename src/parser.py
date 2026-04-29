def load_testcase(path):
    import json
    import os

    streams_path = os.path.join(path, "examples", "test_case_1", "streams.json")
    topology_path = os.path.join(path, "examples", "test_case_1", "topology.json")

    with open(streams_path) as f:
        streams = json.load(f)["streams"]

    with open(topology_path) as f:
        topology = json.load(f)["topology"]

    return streams, topology