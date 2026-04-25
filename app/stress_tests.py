import threading
import random
from concurrent.futures import ThreadPoolExecutor
from books import get_all_books, add_book
from reservations import make_reservation, return_book

MEMBERS = [f"Member_{i}" for i in range(20)]


def _pick_books():
    books = get_all_books()
    if not books:
        print("[!] No books in catalogue.")
    return books


# ---------------------------------------------------------------------------
# Stress Test 1 - single client hammers the same book as fast as possible
# ---------------------------------------------------------------------------
def stress_test_1(n=1000):
    print("\n=== Stress Test 1: Rapid repeated requests (single client) ===")

    books = _pick_books()
    if not books:
        return

    book = max(books, key=lambda b: b.available_copies)
    member = "stress_member_1"
    succeeded = 0
    rejected = 0
    errors = 0

    for i in range(n):
        try:
            res_id = make_reservation(book.book_id, member)
            if res_id:
                succeeded += 1
            else:
                rejected += 1
        except Exception as e:
            errors += 1
            print(f"  [ST1 error {i}] {e}")

    print(f"  Succeeded:          {succeeded}")
    print(f"  Rejected (no copy): {rejected}")
    print(f"  Errors:             {errors}")


# ---------------------------------------------------------------------------
# Stress Test 2 - multiple concurrent clients, random books and members
# ---------------------------------------------------------------------------
def stress_test_2(n=1000, workers=10):
    print(f"\n=== Stress Test 2: Concurrent mixed workload ({workers} workers) ===")

    books = _pick_books()
    if not books:
        return

    counts = {"reserved": 0, "returned": 0, "rejected": 0, "errors": 0}
    active_reservations = []
    lock = threading.Lock()

    def random_action(_):
        book = random.choice(books)
        member = random.choice(MEMBERS)

        # 30% chance to return a book if any are active
        with lock:
            should_return = active_reservations and random.random() < 0.3

        if should_return:
            with lock:
                if not active_reservations:  # re-check after acquiring lock
                    return
                res_id = random.choice(active_reservations)
                active_reservations.remove(res_id)
            try:
                return_book(res_id)
                with lock:
                    counts["returned"] += 1
            except Exception as e:
                print(f"  [ST2 return error] {e}")
                with lock:
                    counts["errors"] += 1
        else:
            try:
                res_id = make_reservation(book.book_id, member)
                with lock:
                    if res_id:
                        active_reservations.append(res_id)
                        counts["reserved"] += 1
                    else:
                        counts["rejected"] += 1
            except Exception as e:
                with lock:
                    counts["errors"] += 1
                print(f"  [ST2 error] {e}")

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(random_action, range(n)))

    print(f"  Reserved:  {counts['reserved']}")
    print(f"  Returned:  {counts['returned']}")
    print(f"  Rejected:  {counts['rejected']}")
    print(f"  Errors:    {counts['errors']}")


# ---------------------------------------------------------------------------
# Stress Test 3 - two clients race to exhaust a single book's copies
# ---------------------------------------------------------------------------
def stress_test_3(books=1000, requests_per_client=1000):
    print(f"\n=== Stress Test 3: Two clients racing for {books} copies ===")
    print(f"    Each client fires {requests_per_client} requests simultaneously.\n")

    book_id = add_book("RaceBook [ST3]", "Stress Tester", books)
    if not book_id:
        print("[!] Could not create test book.")
        return

    results = {"A": 0, "B": 0, "rejected": 0, "errors": 0}
    lock = threading.Lock()

    def client(name):
        for _ in range(requests_per_client):
            member = random.choice(MEMBERS)
            try:
                res_id = make_reservation(book_id, member)
                with lock:
                    if res_id:
                        results[name] += 1
                    else:
                        results["rejected"] += 1
            except Exception as e:
                with lock:
                    results["errors"] += 1
                print(f"  [ST3/{name} error] {e}")

    t1 = threading.Thread(target=client, args=("A",))
    t2 = threading.Thread(target=client, args=("B",))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    total = results["A"] + results["B"]
    print(f"  Client A reserved: {results['A']}")
    print(f"  Client B reserved: {results['B']}")
    print(f"  Rejected (no copy left): {results['rejected']}")
    print(f"  Errors:            {results['errors']}")
    print(f"  Total reserved:    {total} / {books} books")

    if total <= books:
        print("All good - no over-reservation.")
    else:
        print("Over-reservation detected!")