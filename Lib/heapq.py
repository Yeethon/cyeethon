"Heap queue algorithm (a.k.a. priority queue).\n\nHeaps are arrays for which a[k] <= a[2*k+1] and a[k] <= a[2*k+2] for\nall k, counting elements from 0.  For the sake of comparison,\nnon-existing elements are considered to be infinite.  The interesting\nproperty of a heap is that a[0] is always its smallest element.\n\nUsage:\n\nheap = []            # creates an empty heap\nheappush(heap, item) # pushes a new item on the heap\nitem = heappop(heap) # pops the smallest item from the heap\nitem = heap[0]       # smallest item on the heap without popping it\nheapify(x)           # transforms list into a heap, in-place, in linear time\nitem = heapreplace(heap, item) # pops and returns smallest item, and adds\n                               # new item; the heap size is unchanged\n\nOur API differs from textbook heap algorithms as follows:\n\n- We use 0-based indexing.  This makes the relationship between the\n  index for a node and the indexes for its children slightly less\n  obvious, but is more suitable since Python uses 0-based indexing.\n\n- Our heappop() method returns the smallest item, not the largest.\n\nThese two make it possible to view the heap as a regular Python list\nwithout surprises: heap[0] is the smallest item, and heap.sort()\nmaintains the heap invariant!\n"
__about__ = 'Heap queues\n\n[explanation by François Pinard]\n\nHeaps are arrays for which a[k] <= a[2*k+1] and a[k] <= a[2*k+2] for\nall k, counting elements from 0.  For the sake of comparison,\nnon-existing elements are considered to be infinite.  The interesting\nproperty of a heap is that a[0] is always its smallest element.\n\nThe strange invariant above is meant to be an efficient memory\nrepresentation for a tournament.  The numbers below are `k\', not a[k]:\n\n                                   0\n\n                  1                                 2\n\n          3               4                5               6\n\n      7       8       9       10      11      12      13      14\n\n    15 16   17 18   19 20   21 22   23 24   25 26   27 28   29 30\n\n\nIn the tree above, each cell `k\' is topping `2*k+1\' and `2*k+2\'.  In\na usual binary tournament we see in sports, each cell is the winner\nover the two cells it tops, and we can trace the winner down the tree\nto see all opponents s/he had.  However, in many computer applications\nof such tournaments, we do not need to trace the history of a winner.\nTo be more memory efficient, when a winner is promoted, we try to\nreplace it by something else at a lower level, and the rule becomes\nthat a cell and the two cells it tops contain three different items,\nbut the top cell "wins" over the two topped cells.\n\nIf this heap invariant is protected at all time, index 0 is clearly\nthe overall winner.  The simplest algorithmic way to remove it and\nfind the "next" winner is to move some loser (let\'s say cell 30 in the\ndiagram above) into the 0 position, and then percolate this new 0 down\nthe tree, exchanging values, until the invariant is re-established.\nThis is clearly logarithmic on the total number of items in the tree.\nBy iterating over all items, you get an O(n ln n) sort.\n\nA nice feature of this sort is that you can efficiently insert new\nitems while the sort is going on, provided that the inserted items are\nnot "better" than the last 0\'th element you extracted.  This is\nespecially useful in simulation contexts, where the tree holds all\nincoming events, and the "win" condition means the smallest scheduled\ntime.  When an event schedule other events for execution, they are\nscheduled into the future, so they can easily go into the heap.  So, a\nheap is a good structure for implementing schedulers (this is what I\nused for my MIDI sequencer :-).\n\nVarious structures for implementing schedulers have been extensively\nstudied, and heaps are good for this, as they are reasonably speedy,\nthe speed is almost constant, and the worst case is not much different\nthan the average case.  However, there are other representations which\nare more efficient overall, yet the worst cases might be terrible.\n\nHeaps are also very useful in big disk sorts.  You most probably all\nknow that a big sort implies producing "runs" (which are pre-sorted\nsequences, which size is usually related to the amount of CPU memory),\nfollowed by a merging passes for these runs, which merging is often\nvery cleverly organised[1].  It is very important that the initial\nsort produces the longest runs possible.  Tournaments are a good way\nto that.  If, using all the memory available to hold a tournament, you\nreplace and percolate items that happen to fit the current run, you\'ll\nproduce runs which are twice the size of the memory for random input,\nand much better for input fuzzily ordered.\n\nMoreover, if you output the 0\'th item on disk and get an input which\nmay not fit in the current tournament (because the value "wins" over\nthe last output value), it cannot fit in the heap, so the size of the\nheap decreases.  The freed memory could be cleverly reused immediately\nfor progressively building a second heap, which grows at exactly the\nsame rate the first heap is melting.  When the first heap completely\nvanishes, you switch heaps and start a new run.  Clever and quite\neffective!\n\nIn a word, heaps are useful memory structures to know.  I use them in\na few applications, and I think it is good to keep a `heap\' module\naround. :-)\n\n--------------------\n[1] The disk balancing algorithms which are current, nowadays, are\nmore annoying than clever, and this is a consequence of the seeking\ncapabilities of the disks.  On devices which cannot seek, like big\ntape drives, the story was quite different, and one had to be very\nclever to ensure (far in advance) that each tape movement will be the\nmost effective possible (that is, will best participate at\n"progressing" the merge).  Some tapes were even able to read\nbackwards, and this was also used to avoid the rewinding time.\nBelieve me, real good tape sorts were quite spectacular to watch!\nFrom all times, sorting has always been a Great Art! :-)\n'
__all__ = [
    "heappush",
    "heappop",
    "heapify",
    "heapreplace",
    "merge",
    "nlargest",
    "nsmallest",
    "heappushpop",
]


def heappush(heap, item):
    "Push item onto heap, maintaining the heap invariant."
    heap.append(item)
    _siftdown(heap, 0, (len(heap) - 1))


def heappop(heap):
    "Pop the smallest item off the heap, maintaining the heap invariant."
    lastelt = heap.pop()
    if heap:
        returnitem = heap[0]
        heap[0] = lastelt
        _siftup(heap, 0)
        return returnitem
    return lastelt


def heapreplace(heap, item):
    "Pop and return the current smallest value, and add the new item.\n\n    This is more efficient than heappop() followed by heappush(), and can be\n    more appropriate when using a fixed-size heap.  Note that the value\n    returned may be larger than item!  That constrains reasonable uses of\n    this routine unless written as part of a conditional replacement:\n\n        if item > heap[0]:\n            item = heapreplace(heap, item)\n    "
    returnitem = heap[0]
    heap[0] = item
    _siftup(heap, 0)
    return returnitem


def heappushpop(heap, item):
    "Fast version of a heappush followed by a heappop."
    if heap and (heap[0] < item):
        (item, heap[0]) = (heap[0], item)
        _siftup(heap, 0)
    return item


def heapify(x):
    "Transform list into a heap, in-place, in O(len(x)) time."
    n = len(x)
    for i in reversed(range((n // 2))):
        _siftup(x, i)


def _heappop_max(heap):
    "Maxheap version of a heappop."
    lastelt = heap.pop()
    if heap:
        returnitem = heap[0]
        heap[0] = lastelt
        _siftup_max(heap, 0)
        return returnitem
    return lastelt


def _heapreplace_max(heap, item):
    "Maxheap version of a heappop followed by a heappush."
    returnitem = heap[0]
    heap[0] = item
    _siftup_max(heap, 0)
    return returnitem


def _heapify_max(x):
    "Transform list into a maxheap, in-place, in O(len(x)) time."
    n = len(x)
    for i in reversed(range((n // 2))):
        _siftup_max(x, i)


def _siftdown(heap, startpos, pos):
    newitem = heap[pos]
    while pos > startpos:
        parentpos = (pos - 1) >> 1
        parent = heap[parentpos]
        if newitem < parent:
            heap[pos] = parent
            pos = parentpos
            continue
        break
    heap[pos] = newitem


def _siftup(heap, pos):
    endpos = len(heap)
    startpos = pos
    newitem = heap[pos]
    childpos = (2 * pos) + 1
    while childpos < endpos:
        rightpos = childpos + 1
        if (rightpos < endpos) and (not (heap[childpos] < heap[rightpos])):
            childpos = rightpos
        heap[pos] = heap[childpos]
        pos = childpos
        childpos = (2 * pos) + 1
    heap[pos] = newitem
    _siftdown(heap, startpos, pos)


def _siftdown_max(heap, startpos, pos):
    "Maxheap variant of _siftdown"
    newitem = heap[pos]
    while pos > startpos:
        parentpos = (pos - 1) >> 1
        parent = heap[parentpos]
        if parent < newitem:
            heap[pos] = parent
            pos = parentpos
            continue
        break
    heap[pos] = newitem


def _siftup_max(heap, pos):
    "Maxheap variant of _siftup"
    endpos = len(heap)
    startpos = pos
    newitem = heap[pos]
    childpos = (2 * pos) + 1
    while childpos < endpos:
        rightpos = childpos + 1
        if (rightpos < endpos) and (not (heap[rightpos] < heap[childpos])):
            childpos = rightpos
        heap[pos] = heap[childpos]
        pos = childpos
        childpos = (2 * pos) + 1
    heap[pos] = newitem
    _siftdown_max(heap, startpos, pos)


def merge(*iterables, key=None, reverse=False):
    "Merge multiple sorted inputs into a single sorted output.\n\n    Similar to sorted(itertools.chain(*iterables)) but returns a generator,\n    does not pull the data into memory all at once, and assumes that each of\n    the input streams is already sorted (smallest to largest).\n\n    >>> list(merge([1,3,5,7], [0,2,4,8], [5,10,15,20], [], [25]))\n    [0, 1, 2, 3, 4, 5, 5, 7, 8, 10, 15, 20, 25]\n\n    If *key* is not None, applies a key function to each element to determine\n    its sort order.\n\n    >>> list(merge(['dog', 'horse'], ['cat', 'fish', 'kangaroo'], key=len))\n    ['dog', 'cat', 'fish', 'horse', 'kangaroo']\n\n    "
    h = []
    h_append = h.append
    if reverse:
        _heapify = _heapify_max
        _heappop = _heappop_max
        _heapreplace = _heapreplace_max
        direction = -1
    else:
        _heapify = heapify
        _heappop = heappop
        _heapreplace = heapreplace
        direction = 1
    if key is None:
        for (order, it) in enumerate(map(iter, iterables)):
            try:
                next = it.__next__
                h_append([next(), (order * direction), next])
            except StopIteration:
                pass
        _heapify(h)
        while len(h) > 1:
            try:
                while True:
                    (value, order, next) = s = h[0]
                    (yield value)
                    s[0] = next()
                    _heapreplace(h, s)
            except StopIteration:
                _heappop(h)
        if h:
            (value, order, next) = h[0]
            (yield value)
            (yield from next.__self__)
        return
    for (order, it) in enumerate(map(iter, iterables)):
        try:
            next = it.__next__
            value = next()
            h_append([key(value), (order * direction), value, next])
        except StopIteration:
            pass
    _heapify(h)
    while len(h) > 1:
        try:
            while True:
                (key_value, order, value, next) = s = h[0]
                (yield value)
                value = next()
                s[0] = key(value)
                s[2] = value
                _heapreplace(h, s)
        except StopIteration:
            _heappop(h)
    if h:
        (key_value, order, value, next) = h[0]
        (yield value)
        (yield from next.__self__)


def nsmallest(n, iterable, key=None):
    "Find the n smallest elements in a dataset.\n\n    Equivalent to:  sorted(iterable, key=key)[:n]\n    "
    if n == 1:
        it = iter(iterable)
        sentinel = object()
        result = min(it, default=sentinel, key=key)
        return [] if (result is sentinel) else [result]
    try:
        size = len(iterable)
    except (TypeError, AttributeError):
        pass
    else:
        if n >= size:
            return sorted(iterable, key=key)[:n]
    if key is None:
        it = iter(iterable)
        result = [(elem, i) for (i, elem) in zip(range(n), it)]
        if not result:
            return result
        _heapify_max(result)
        top = result[0][0]
        order = n
        _heapreplace = _heapreplace_max
        for elem in it:
            if elem < top:
                _heapreplace(result, (elem, order))
                (top, _order) = result[0]
                order += 1
        result.sort()
        return [elem for (elem, order) in result]
    it = iter(iterable)
    result = [(key(elem), i, elem) for (i, elem) in zip(range(n), it)]
    if not result:
        return result
    _heapify_max(result)
    top = result[0][0]
    order = n
    _heapreplace = _heapreplace_max
    for elem in it:
        k = key(elem)
        if k < top:
            _heapreplace(result, (k, order, elem))
            (top, _order, _elem) = result[0]
            order += 1
    result.sort()
    return [elem for (k, order, elem) in result]


def nlargest(n, iterable, key=None):
    "Find the n largest elements in a dataset.\n\n    Equivalent to:  sorted(iterable, key=key, reverse=True)[:n]\n    "
    if n == 1:
        it = iter(iterable)
        sentinel = object()
        result = max(it, default=sentinel, key=key)
        return [] if (result is sentinel) else [result]
    try:
        size = len(iterable)
    except (TypeError, AttributeError):
        pass
    else:
        if n >= size:
            return sorted(iterable, key=key, reverse=True)[:n]
    if key is None:
        it = iter(iterable)
        result = [(elem, i) for (i, elem) in zip(range(0, (-n), (-1)), it)]
        if not result:
            return result
        heapify(result)
        top = result[0][0]
        order = -n
        _heapreplace = heapreplace
        for elem in it:
            if top < elem:
                _heapreplace(result, (elem, order))
                (top, _order) = result[0]
                order -= 1
        result.sort(reverse=True)
        return [elem for (elem, order) in result]
    it = iter(iterable)
    result = [(key(elem), i, elem) for (i, elem) in zip(range(0, (-n), (-1)), it)]
    if not result:
        return result
    heapify(result)
    top = result[0][0]
    order = -n
    _heapreplace = heapreplace
    for elem in it:
        k = key(elem)
        if top < k:
            _heapreplace(result, (k, order, elem))
            (top, _order, _elem) = result[0]
            order -= 1
    result.sort(reverse=True)
    return [elem for (k, order, elem) in result]


try:
    from _heapq import *
except ImportError:
    pass
try:
    from _heapq import _heapreplace_max
except ImportError:
    pass
try:
    from _heapq import _heapify_max
except ImportError:
    pass
try:
    from _heapq import _heappop_max
except ImportError:
    pass
if __name__ == "__main__":
    import doctest

    print(doctest.testmod())
