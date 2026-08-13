from functools import lru_cache

def max_score(s: str) -> int:
    """
    Compute maximum score for removing groups from string s,
    where removing a group of k identical chars gives k*k points.
    """
    arr = list(s)  # convert to list of chars for fast indexing

    @lru_cache(None)
    def dp(l: int, r: int, k: int) -> int:
        """
        dp(l, r, k) = maximum score achievable from subarray arr[l..r]
        if there are k extra characters equal to arr[r] attached to the right
        of position r (i.e., we treat arr[r] as already having k same-colored
        characters merged with it).
        """
        if l > r:
            return 0

        # 1) compress the tail: merge consecutive same chars at the end
        while r > l and arr[r] == arr[r - 1]:
            r -= 1
            k += 1

        # 2) option A: remove the final group (arr[r] plus k attached ones) now
        best = dp(l, r - 1, 0) + (k + 1) * (k + 1)

        # 3) option B: try to merge arr[r] with an earlier equal char arr[i]
        # so they form a bigger group (we remove the middle part first)
        for i in range(l, r):
            if arr[i] == arr[r]:
                candidate = dp(i + 1, r - 1, 0) + dp(l, i, k + 1)
                if candidate > best:
                    best = candidate

        return best

    return dp(0, len(arr) - 1, 0)


# Example usage
if __name__ == "__main__":
    tests = ["aabbaac", "AABBA", "", "aa", "ababa"]
    for t in tests:
        print(t, "->", max_score(t))

