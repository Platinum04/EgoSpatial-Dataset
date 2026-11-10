"""Run a layer-search permutation control on an archived 11-A activation file."""

import argparse
import json

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", help="hidden_last_token.npz from g4_study.py")
    parser.add_argument("--permutations", type=int, default=99)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    if args.permutations < 1:
        parser.error("--permutations must be positive")

    with np.load(args.archive, allow_pickle=False) as archive:
        gold = archive["gold"]
        mask = (archive["task"] == "egocentric") & np.isin(gold, ["left", "right"])
        hidden = archive["H"][mask].astype(np.float32)
        groups = archive["groups"][mask]
    labels = gold[mask] == "right"
    n_groups = len(np.unique(groups))
    if n_groups < 2:
        parser.error("the archive must contain at least two egocentric lateral groups")

    splits = list(GroupKFold(n_splits=min(5, n_groups)).split(hidden, labels, groups))
    if any(np.unique(labels[train]).size < 2 for train, _ in splits):
        parser.error("every training fold must contain both labels")

    # Preserve each group's label counts while breaking within-group associations.
    group_indices = [np.flatnonzero(groups == group) for group in np.unique(groups)]
    movable_groups = [indices for indices in group_indices if np.unique(labels[indices]).size == 2]
    if not movable_groups:
        parser.error("no group contains both labels, so within-group shuffling is undefined")

    def layer_scores(target):
        scores = []
        for layer in range(hidden.shape[1]):
            features = hidden[:, layer]
            fold_scores = []
            for train, test in splits:
                probe = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=2000))
                probe.fit(features[train], target[train])
                fold_scores.append(probe.score(features[test], target[test]))
            scores.append(float(np.mean(fold_scores)))
        return scores

    rng = np.random.default_rng(args.seed)
    with threadpool_limits(limits=1):
        observed = layer_scores(labels)
        null = []
        for _ in range(args.permutations):
            shuffled = labels.copy()
            for indices in movable_groups:
                shuffled[indices] = rng.permutation(labels[indices])
            null.append(max(layer_scores(shuffled)))

    best = max(observed)
    print(json.dumps({
        "examples": len(labels),
        "groups": n_groups,
        "groups_with_both_labels": len(movable_groups),
        "seed": args.seed,
        "permutations": args.permutations,
        "best_layer": int(np.argmax(observed)),
        "observed_max": best,
        "observed_per_layer": observed,
        "null_maxima": null,
        "p_value": (1 + sum(score >= best for score in null)) / (1 + len(null)),
    }, indent=2))


if __name__ == "__main__":
    main()
