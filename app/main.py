import uuid
from schema import init_schema
from books import seed_books
from books import get_all_books, add_book, update_book_copies, reinitialize
from reservations import (
    make_reservation,
    return_book,
    get_reservations_by_member,
)
from seed_data import seed_data
from stress_tests import stress_test_1, stress_test_2, stress_test_3
from db import shutdown


def select_book_flow(only_available=False):
    books = get_all_books()
    if only_available:
        books = [b for b in books if b.available_copies > 0]

    if not books:
        print("[!] No books found." if not only_available else "[!] No books currently available.")
        return None

    print()
    for i, b in enumerate(books, 1):
        avail = f"{b.available_copies}/{b.total_copies}"
        print(f"  {i}. {b.title} by {b.author}  [{avail} available]")

    choice = input("Select book number (Enter to cancel): ").strip()
    if not choice:
        return None

    try:
        return books[int(choice) - 1]
    except (ValueError, IndexError):
        print("[!] Invalid selection.")
        return None


def select_reservation_flow():
    member_name = input("Member name: ").strip()
    rows = get_reservations_by_member(member_name)

    if not rows:
        return None

    print("\nSelect reservation:")
    for i, r in enumerate(rows, 1):
        print(
            f"  {i}. [{r.status}] {r.book_title} — "
            f"{r.reserved_on.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    choice = input("Number (Enter to cancel): ").strip()
    if not choice:
        return None

    try:
        return rows[int(choice) - 1]
    except (ValueError, IndexError):
        print("[!] Invalid selection.")
        return None


def add_book_flow():
    title = input("Title: ").strip()
    author = input("Author: ").strip()
    if not title or not author:
        print("[!] Title and author are required.")
        return

    try:
        copies = int(input("Number of copies: ").strip())
        if copies <= 0:
            raise ValueError
    except ValueError:
        print("[!] Copies must be a positive integer.")
        return

    add_book(title, author, copies)


def update_copies_flow():
    book = select_book_flow()
    if not book:
        return

    print(f"\n  '{book.title}' — {book.available_copies}/{book.total_copies} available")
    raw = input("Adjust by (e.g. +2 or -1): ").strip()

    try:
        delta = int(raw)
        if delta == 0:
            print("[!] Delta cannot be zero.")
            return
    except ValueError:
        print("[!] Enter a number like +2 or -1.")
        return

    update_book_copies(book.book_id, delta)


def menu():
    init_schema()
    seed_books()

    while True:
        print("""
Library Reservation System
-- Reservations ----------
1. Make reservation
2. View my reservations
3. Return a book
-- Books -----------------
4. List all books
5. Add a book
6. Update book copies
-- Data ------------------
7. Seed bulk data
8. Reinitialize data
9. Stress Test 1
10. Stress Test 2
11. Stress Test 3
--------------------------
0. Exit
""")
        choice = input("Choice: ").strip()

        if choice == '1':
            book = select_book_flow(only_available=True)
            if not book:
                continue
            member_name = input("Member name: ").strip()
            if not member_name:
                print("[!] Missing member name.")
                continue
            make_reservation(book.book_id, member_name)

        elif choice == '2':
            member_name = input("Member name: ").strip()
            if not member_name:
                print("[!] Missing member name.")
                continue
            get_reservations_by_member(member_name)

        elif choice == '3':
            selected = select_reservation_flow()
            if not selected:
                continue
            if selected.status == 'RETURNED':
                print("[!] Already returned.")
                continue
            return_book(selected.reservation_id)

        elif choice == '4':
            books = get_all_books()
            if not books:
                print("[!] No books in catalogue.")
            else:
                print(f"\n--- Catalogue ({len(books)} books) ---")
                for b in books:
                    print(f"  {b.title} by {b.author}  [{b.available_copies}/{b.total_copies} available]")

        elif choice == '5':
            add_book_flow()

        elif choice == '6':
            update_copies_flow()

        elif choice == '7':
            try:
                n = int(input("How many distinct books to seed? [1000]: ") or 1000)
                total_copies = int(input("How many books copies to seed? [10000]: ") or 10000)
                seed_data(n, total_copies)
            except ValueError:
                print("[!] Invalid number.")

        elif choice == '8':
            confirm = input("This will wipe all data and restore initial books. Continue? (y/N): ").strip().lower()
            if confirm == 'y': reinitialize()

        elif choice == '9':
            stress_test_1()
        elif choice == '10':
            stress_test_2()
        elif choice == '11':
            stress_test_3()

        elif choice == '0':
            break

        else:
            print("[!] Unknown option.")


if __name__ == '__main__':
    try:
        menu()
    finally:
        shutdown()