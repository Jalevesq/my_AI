
from AI import run_conversation

def main():
    while True:
        _query = input("Ask a question: ")
        if _query == "exit":
            break
        if not _query:
            continue
        run_conversation(_query)
main()