import random
from books import add_book


def seed_data(n=1000, total_copies=10000):
    """Seed n distinct books where available copies are randomly distributed across all books, summing to total_copies."""

    breakpoints = sorted(random.sample(range(1, total_copies), n - 1))
    splits = [0] + breakpoints + [total_copies]
    copy_counts = [splits[i+1] - splits[i] for i in range(n)]

    print(f"[seed] Seeding {n} books with {total_copies} total copies...")
    for i, copies in enumerate(copy_counts, start=1):
        add_book(f"Book_{i}", f"Author_{i}", copies)

    print(f"[seed] Done - {n} books seeded, {total_copies} copies total.")