"""
Utilities.
"""


def get_coverage_cutoff(upvotes: list[int], threshold: float):
    """
    ...

    Note: the caller is responsible for ensuring that comments exists.
    """
    covered_upvote = threshold_upvote = cutoff = 0
    totol_comments = len(upvotes)

    for iteration, upvote in enumerate(upvotes):
        covered_upvote += upvote

        remaining_upvote = (totol_comments - (iteration + 1)) * upvote
        upvote_coverage = covered_upvote / (covered_upvote + remaining_upvote)

        if upvote_coverage >= threshold:
            threshold_upvote = upvote
            cutoff = iteration + 1
            break
    else:
        threshold_upvote = upvotes[-1]
        cutoff = totol_comments
    return cutoff, threshold_upvote


def filter_thread():
    raise NotImplementedError


# =========================================================
if __name__ == "__main__":
    test_upvotes = [100, 50, 25, 12, 6, 3, 2, 1, 1, 0]
    # comment_with_upvote = {}

    if test_upvotes[0] == 0:
        ...
    else:
        foo, bar = get_coverage_cutoff(test_upvotes, threshold=0.9)
    # result = filter_thread(comment_with_upvote, foo, bar)
