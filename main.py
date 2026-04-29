from src.parser import load_testcase

def main():
    streams, topology = load_testcase(".")

    print("STREAMS:")
    print(streams)

    print("\nTOPOLOGY:")
    print(topology)

if __name__ == "__main__":
    main()