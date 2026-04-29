import uuid
from schema import session, init_schema, prepare_queries

init_schema()
Q = prepare_queries()

INITIAL_BOOKS = [
    ("Dune",       "Frank Herbert",  2),
    ("1984",       "George Orwell",  3),
    ("The Hobbit", "J.R.R. Tolkien", 1)
]


def seed_books():
    existing = list(session.execute(Q["SELECT_ONE_BOOK_ID"]))
    if existing:
        return
    for title, author, copies in INITIAL_BOOKS:
        session.execute(Q["INSERT_BOOK"], (uuid.uuid4(), title, author, copies, copies))
    print(f"[books] Seeded {len(INITIAL_BOOKS)} books.")


def reinitialize():
    print("[reinit] Clearing all reservations...")
    for row in session.execute(Q["SELECT_ALL_RESERVATION_IDS"]):
        session.execute(Q["DELETE_RESERVATION"], (row.reservation_id,))

    print("[reinit] Clearing reservations_by_member...")
    for row in session.execute(Q["SELECT_ALL_MEMBERS"]):
        session.execute(Q["DELETE_RESERVATIONS_BY_MEMBER"], (row.member_name,))

    print("[reinit] Clearing reservations_by_book...")
    for row in session.execute(Q["SELECT_ALL_BOOKS"]):
        session.execute(Q["DELETE_RESERVATIONS_BY_BOOK"], (row.book_id,))

    print("[reinit] Clearing all books...")
    for row in session.execute(Q["SELECT_ALL_BOOKS"]):
        session.execute(Q["DELETE_BOOK"], (row.book_id,))

    print("[reinit] Seeding initial books...")
    for title, author, copies in INITIAL_BOOKS:
        session.execute(Q["INSERT_BOOK"], (uuid.uuid4(), title, author, copies, copies))
    print("[reinit] Done.")


def get_all_books():
    return list(session.execute(Q["SELECT_ALL_BOOKS"]))


def add_book(title, author, copies):
    book_id = uuid.uuid4()
    session.execute(Q["INSERT_BOOK"], (book_id, title, author, copies, copies))
    print(f"[+] Added '{title}' by {author} ({copies} copies) - ID: {book_id}")
    return book_id


def update_book_copies(book_id, delta, *, reason="manual adjustment"):
    for _ in range(100):
        row = session.execute(Q["SELECT_BOOK_COPIES_FULL"], (book_id,)).one()

        if not row:
            print("[!] Book not found.")
            return False

        new_total = row.total_copies + delta
        new_available = row.available_copies + delta

        if new_total < 0:
            print(f"[!] Cannot reduce below 0 total copies (current: {row.total_copies}).")
            return False

        if new_available < 0:
            in_use = row.total_copies - row.available_copies
            print(
                f"[!] {in_use} cop{'y' if in_use == 1 else 'ies'} currently reserved - "
                f"can only reduce by {row.available_copies} at most."
            )
            return False

        applied = session.execute(
            Q["UPDATE_BOOK_COPIES_FULL_CAS"],
            (new_total, new_available, book_id, row.available_copies)
        ).one()

        if applied.applied:
            break
    else:
        print("[!] Update failed due to heavy system load - please try again.")
        return False

    print(f"[~] '{row.title}' copies: {row.total_copies} → {new_total} ({reason})")
    return True