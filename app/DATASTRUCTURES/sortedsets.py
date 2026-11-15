import random

class Node:
    def __init__(self, value, score, level):
        self.value = value
        self.score = float("-inf") if score is None else float(score)
        self.forward = [None] * (level + 1)

class SortedSet:
    def __init__(self, max_level=16, p=0.5):
        self.max_level = max_level
        self.p = p
        self.header = Node(None, None, max_level)
        self.level = 0
        self.size = 0
        
    def random_level(self):
        level = 0
        while random.random() < self.p and level < self.max_level:
            level += 1
        return level
    
    def insert(self, value, score):
        update = [None] * (self.max_level + 1)
        current = self.header
        
        for i in range(self.level, -1, -1):
            while current.forward[i] and current.forward[i].score < score:
                current = current.forward[i]
            update[i] = current
        
        current = current.forward[0]
        
        if current is None or current.score != score:
            new_level = self.random_level()
            if new_level > self.level:
                for i in range(self.level + 1, new_level + 1):
                    update[i] = self.header
                self.level = new_level
            
            new_node = Node(value, score, new_level)
            for i in range(new_level + 1):
                new_node.forward[i] = update[i].forward[i]
                update[i].forward[i] = new_node
            
            self.size += 1
            
    def search(self, score):
        current = self.header
        for i in range(self.level, -1, -1):
            while current.forward[i] and current.forward[i].score < score:
                current = current.forward[i]
        
        current = current.forward[0]
        if current and current.score == score:
            return current.value
        return None
    
    def delete(self, score):
        update = [None] * (self.max_level + 1)
        current = self.header
        
        for i in range(self.level, -1, -1):
            while current.forward[i] and current.forward[i].score < score:
                current = current.forward[i]
            update[i] = current
        
        current = current.forward[0]
        
        if current and current.score == score:
            for i in range(self.level + 1):
                if update[i].forward[i] != current:
                    break
                update[i].forward[i] = current.forward[i]
            
            while self.level > 0 and self.header.forward[self.level] is None:
                self.level -= 1
            
            self.size -= 1
            
    def display_generator(self, reverse=False, offset=0, count=None):
        current = self.header.forward[0]
        if reverse:
            # Collect all nodes in a list to reverse them
            nodes = []
            while current:
                nodes.append(current)
                current = current.forward[0]
            nodes.reverse()
            current = nodes[offset:] if count is None else nodes[offset:offset + count]
        else:
            current = current.forward[0]
            for _ in range(offset):
                if current is None:
                    return
                current = current.forward[0]
            if count is not None:
                end = offset + count
                current = [current] + [current.forward[0] for _ in range(count - 1) if current and current.forward[0]]
            else:
                current = [current]
                
        for node in current:
            if node is None:
                break
            yield (node.value, node.score)