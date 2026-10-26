from itertools import combinations

import networkx as nx

IDENTITY_FIELDS = ["name", "address", "phone", "email"]


def find_real_users(users):
    graph = nx.Graph()
    graph.add_nodes_from(users["id"])

    for fields in combinations(IDENTITY_FIELDS, len(IDENTITY_FIELDS) - 1):
        fields = list(fields)
        known = users.dropna(subset=fields)
        for _, group in known.groupby(fields):
            ids = list(group["id"])
            for other in ids[1:]:
                graph.add_edge(ids[0], other)

    owner = {}
    for person in nx.connected_components(graph):
        first_id = min(person)
        for user_id in person:
            owner[user_id] = first_id
    return users["id"].map(owner)
