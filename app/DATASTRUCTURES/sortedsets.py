import random


class Node:
    def __init__(self, member, score, level):
        self.member = member
        self.score = score
        self.forward = [None] * (level + 1)

    def key(self):
        # Redis orders by score, then by member (lexicographically) on ties.
        return (self.score, self.member)


class SortedSet:
    """Skip list ordered by (score, member), plus a member -> score dict.

    The dict makes membership and score lookups O(1); the skip list keeps
    members in sorted order for range queries.
    """

    def __init__(self, max_level=16, p=0.5):
        self.max_level = max_level
        self.p = p
        self.header = Node(None, float("-inf"), max_level)
        self.level = 0
        self.scores = {}

    def __len__(self):
        return len(self.scores)

    def __contains__(self, member):
        return member in self.scores

    def score(self, member):
        return self.scores.get(member)

    def _random_level(self):
        level = 0
        while random.random() < self.p and level < self.max_level:
            level += 1
        return level

    def _find_update(self, key):
        """Return the rightmost node before `key` at every level."""
        update = [self.header] * (self.max_level + 1)
        current = self.header
        for i in range(self.level, -1, -1):
            while current.forward[i] and current.forward[i].key() < key:
                current = current.forward[i]
            update[i] = current
        return update

    def _insert_node(self, member, score):
        update = self._find_update((score, member))
        new_level = self._random_level()
        if new_level > self.level:
            self.level = new_level
        node = Node(member, score, new_level)
        for i in range(new_level + 1):
            node.forward[i] = update[i].forward[i]
            update[i].forward[i] = node

    def _remove_node(self, member, score):
        update = self._find_update((score, member))
        target = update[0].forward[0]
        if target is None or target.member != member:
            return
        for i in range(self.level + 1):
            if update[i].forward[i] is not target:
                break
            update[i].forward[i] = target.forward[i]
        while self.level > 0 and self.header.forward[self.level] is None:
            self.level -= 1

    def add(self, member, score):
        """Insert or update `member`. Return True if the member is new."""
        score = float(score)
        old = self.scores.get(member)
        if old is not None:
            if old == score:
                return False
            self._remove_node(member, old)
            self._insert_node(member, score)
            self.scores[member] = score
            return False
        self._insert_node(member, score)
        self.scores[member] = score
        return True

    def remove(self, member):
        """Remove `member`. Return True if it existed."""
        score = self.scores.pop(member, None)
        if score is None:
            return False
        self._remove_node(member, score)
        return True

    def rank(self, member):
        """0-based position of `member` in sorted order, or None."""
        if member not in self.scores:
            return None
        for i, (m, _) in enumerate(self):
            if m == member:
                return i

    def __iter__(self):
        """Yield (member, score) pairs in ascending order."""
        node = self.header.forward[0]
        while node:
            yield node.member, node.score
            node = node.forward[0]
