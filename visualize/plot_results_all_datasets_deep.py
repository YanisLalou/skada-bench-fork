# %%
import numpy as np
import pandas as pd
import json
import scipy.stats as stats
import argparse


def shade_of_color_pvalue(
    df_value,
    pvalue,
    min_value=0,
    mean_value=0,
    max_value=1,
    color_threshold=0.05,
):
    # Intensity range for the green and red colors
    intensity_range = (10, 60)

    if df_value == "nan" or np.isnan(df_value):
        # Return the nan value
        return df_value
    else:
        if pvalue < color_threshold:
            if df_value > mean_value:
                color_min = mean_value
                color_max = max_value
                if color_max - color_min == 0:
                    # To avoid division by zero
                    intensity = intensity_range[0]
                else:
                    intensity = int(
                        intensity_range[0]
                        + (intensity_range[1] - intensity_range[0])
                        * (df_value - color_min)
                        / (color_max - color_min)
                    )
                return "\\cellcolor{good_color!%d}{%s}" % (intensity, df_value)
            else:
                red_min = min_value
                red_max = mean_value
                if red_min - red_max == 0:
                    # To avoid division by zero
                    intensity = intensity_range[0]
                else:
                    intensity = int(
                        intensity_range[0]
                        + (intensity_range[1] - intensity_range[0])
                        * (df_value - red_max)
                        / (red_min - red_max)
                    )
                return "\\cellcolor{bad_color!%d}{%s}" % (intensity, df_value)
        else:
            return df_value


# %%
def generate_table(csv_file, scorer_selection="unsupervised"):
    scorer_selection = "unsupervised"
    df = pd.read_csv(csv_file)
    df = df.query("estimator != 'NO_DA_SOURCE_ONLY_BASE_ESTIM'")

    df["target_accuracy-test-identity"] = (
        df["target_accuracy-test-identity"]
        .apply(lambda x: json.loads(x))
    )
    df["nb_splits"] = df["target_accuracy-test-identity"].apply(
        lambda x: len(x))
    df_target = df.query(
        'estimator == "Deep_NO_DA_TARGET_ONLY" & scorer == "supervised"')
    df_source = df.query(
        'estimator == "Deep_NO_DA_SOURCE_ONLY" & scorer == "supervised"'
    )
    # idx_source_best_scorer = df_source.groupby(["shift"])[
    #     "target_accuracy-test-mean"
    # ].idxmax()
    # df_source = df_source.loc[idx_source_best_scorer]
    df = df.merge(
        df_target[["shift", "target_accuracy-test-mean",
                   "target_accuracy-test-std"]],
        on="shift",
        suffixes=("", "_target"),
    )
    df = df.merge(
        df_source[
            [
                "shift",
                "target_accuracy-test-mean",
                "target_accuracy-test-std",
                "target_accuracy-test-identity",
            ]
        ],
        on="shift",
        suffixes=("", "_source"),
    )
    # remove rows where the source is better than the target
    df = df[
        df["target_accuracy-test-mean_source"]
        < df["target_accuracy-test-mean_target"]
    ].reset_index()
    df = df.query("nb_splits == 5")

    # remove duplicates
    df = df.drop_duplicates(subset=["dataset", "scorer", "estimator", "shift"])

    # %%
    # # count the number of shifts
    # df_shift = df.groupby(["dataset", "scorer", "estimator"])
    # df_shift = df_shift.agg({"shift": "count"}).reset_index()
    # df_shift["nb_shift"] = df_shift["shift"]
    # nb_shifts_per_dataset = {
    #     "Office31": int(0.8 * 5),
    #     "OfficeHomeResnet": int(0.8 * 12),
    #     "mnist_usps": 2,
    #     "20NewsGroups": int(0.8 * 6),
    #     "AmazonReview": int(0.8 * 11),
    #     "Mushrooms": int(0.8 * 2),
    #     "Phishing": int(0.8 * 2),
    #     "BCI": int(0.8 * 9),
    #     "covariate_shift": 1,
    #     "target_shift": 1,
    #     "concept_drift": 1,
    #     "subspace": 1,
    # }

    # df_shift["nb_shift_max"] = df_shift["dataset"].apply(
    #     lambda x: nb_shifts_per_dataset[x]
    # )

    # df = df.merge(
    #     df_shift[
    #         [
    #             "dataset",
    #             "scorer",
    #             "estimator",
    #             "nb_shift",
    #             "nb_shift_max",
    #         ]
    #     ],
    #     on=["dataset", "scorer", "estimator"],
    # )
    # df = df[df["nb_shift"] >= df["nb_shift_max"]]

# %%
    df_filtered = df.query("estimator != 'Train Tgt'")
    df_filtered = df_filtered.query("estimator != 'Train Src'")
    df_grouped = df_filtered.groupby(["dataset", "scorer", "estimator"])
    wilco = []
    scorer = []
    estimator = []
    dataset = []
    for idx, df_ in df_grouped:
        # test de wilcoxon
        acc_da = np.concatenate(df_["target_accuracy-test-identity"].values)
        acc_source = np.concatenate(
            df_["target_accuracy-test-identity_source"].values)
        try:
            wilco.append(
                stats.wilcoxon(
                    acc_da,
                    acc_source,
                )[1]
            )
            scorer.append(df_["scorer"].values[0])
            estimator.append(df_["estimator"].values[0])
            dataset.append(df_["dataset"].values[0])
        except ValueError:
            wilco.append(1)
            scorer.append(df_["scorer"].values[0])
            estimator.append(df_["estimator"].values[0])
            dataset.append(df_["dataset"].values[0])

    df_wilco = pd.DataFrame(
        {
            "scorer": scorer,
            "estimator": estimator,
            "pvalue": wilco,
            "dataset": dataset,
        }
    )

    df["rank"] = df.groupby(["dataset", "scorer", "shift"])[
        "target_accuracy-test-mean"
    ].rank(ascending=False)

    df_mean = (
        df.groupby(["dataset", "type", "scorer", "estimator"])
        .agg(
            {
                "target_accuracy-test-mean": lambda x: x.mean(skipna=False),
                "target_accuracy-test-std": lambda x: x.mean(skipna=False),
                "rank": lambda x: x.mean(skipna=False),
            }
        )
        .reset_index()
    )

    df_source_mean = df_mean.query(
        "estimator == 'Deep_NO_DA_SOURCE_ONLY' & scorer == 'supervised'")
    df_target_mean = df_mean.query(
        "estimator == 'Deep_NO_DA_TARGET_ONLY' & scorer == 'supervised'")

    if scorer_selection == "supervised":
        df_tot = df_mean.query("scorer == 'supervised'")
        df_wilco = df_wilco.query("scorer == 'supervised'")

    elif scorer_selection == "unsupervised":
        df_mean = df_mean.query(
            "scorer != 'supervised' & scorer != 'best_scorer'")

        df_mean_dataset = (
            df_mean.groupby(["estimator", "scorer"])[
                "target_accuracy-test-mean"
            ]
            .mean()
            .reset_index()
        )

        idx_best_scorer = df_mean_dataset.groupby(["estimator"])[
            "target_accuracy-test-mean"
        ].idxmax()
        df_mean_dataset = df_mean_dataset.loc[idx_best_scorer]

        df_tot = df_mean.merge(
            df_mean_dataset[
                [
                    "estimator",
                    "scorer",
                ]
            ],
            on=[
                "estimator",
            ],
            suffixes=("", "_best"),
        )

        df_tot = df_tot[df_tot["scorer"] ==
                        df_tot["scorer_best"]].reset_index()

        df_wilco = df_wilco[
            ["dataset", "estimator", "scorer", "pvalue"]
        ].merge(
            df_mean_dataset[["estimator", "scorer"]],
            on=[
                "estimator",
            ],
            suffixes=("", "_best"),
        )

        df_wilco = df_wilco[df_wilco["scorer"] ==
                            df_wilco["scorer_best"]].reset_index()

    df_rank = df_tot.groupby(["estimator"])["rank"].mean().reset_index()
    # %%
    df_tot = df_tot.query("estimator != 'Deep_NO_DA_SOURCE_ONLY'")
    df_tot = df_tot.query("estimator != 'Deep_NO_DA_TARGET_ONLY'")
    df_tot = pd.concat(
        [df_tot, df_source_mean, df_target_mean], axis=0).reset_index()

    # %%
    df_tab = df_tot.pivot(
        index="dataset",
        columns=["estimator"],
        values="target_accuracy-test-mean",
    )

    # df_tab = df_tab.reindex(
    #         columns=["NO DA", "Reweighting",
    #             "Mapping", "Subspace", "Other"
    #         ],
    #     level=0,
    # )
    # %%
    df_tab = df_tab.reindex(
        columns=[
            "Deep_NO_DA_SOURCE_ONLY",
            "Deep_NO_DA_TARGET_ONLY",
            "DANN",
            "DeepCORAL",
            "DeepJDOT",
        ],
        level=0,
    )

    # %%
    df_tab = df_tab.T.merge(df_rank, on="estimator")
    # %%
    df_tab = df_tab.merge(
        df_mean_dataset[["estimator", "scorer"]], on="estimator"
    )
    df_tab = df_tab.set_index(["estimator"])
    df_tab = df_tab.round(2)
    # df_tab = df_tab[df_tab.columns[1:]]

    # %%

    # add the colorcell
    for i, col in enumerate(df_tab.columns[:-2]):
        max_value = df_tab.loc[df_tab[col].index[1], col]
        mean_value = df_tab.loc[df_tab[col].index[0], col]
        min_value = df_tab[col].min()
        for idx in df_tab.index[2:]:
            # get the value
            if df_tab.loc[idx, col] == "nan" or np.isnan(df_tab.loc[idx, col]):
                continue
            value = df_tab.loc[idx, col]
            # get the color
            pvalue = df_wilco.query(
                f"estimator == '{idx}' & dataset == '{col}'"
            )["pvalue"].values[0]
            color = shade_of_color_pvalue(
                value,
                pvalue,
                min_value=min_value,
                mean_value=mean_value,
                max_value=max_value,
            )
            df_tab.loc[idx, col] = color
        df_tab.loc[df_tab.index[1], col] = "\\cellcolor{good_color!%d}{%s}" % (
            60,
            df_tab.loc[df_tab.index[1], col],
        )

    # %%
    if scorer == "supervised":
        df_tab = df_tab.reindex(
            columns=[
                "OfficeHome",
                "mnist_usps",
                "BCI",
                "rank",
            ],
        )
    else:
        df_tab = df_tab.reindex(
            columns=[
                "OfficeHome",
                "mnist_usps",
                "BCI",
                "scorer",
                "rank",
            ],
        )
    df_tab = df_tab.rename(
        columns={
            "OfficeHome": r"\mcrot{1}{l}{45}{OfficeHome}",
            "mnist_usps": r"\mcrot{1}{l}{45}{MNIST/USPS}",
            "BCI": r"\mcrot{1}{l}{45}{BCI}",
            "scorer": r"\mcrot{1}{l}{45}{Selected Scorer}",
            "rank": r"\mcrot{1}{l}{45}{Rank}",
        },
        index={
            "Deep_NO_DA_SOURCE_ONLY": "Train Src",
            "Deep_NO_DA_TARGET_ONLY": "Train Tgt",
        }
    )

    df_tab = df_tab.fillna("\\color{gray!90}NA")
    # %%
    # convert to latex
    lat_tab = df_tab.to_latex(
        escape=False,
        multicolumn_format="c",
        multirow=True,
        column_format="|l||rr||r||rr|",
    )
    lat_tab = lat_tab.replace(r"\type & estimator &  &  &  &  \\", "")
    lat_tab = lat_tab.replace("toprule", "hline")
    lat_tab = lat_tab.replace("midrule", "hline")
    if scorer == "supervised":
        lat_tab = lat_tab.replace("cline{1-15}", r"hline\hline")
    else:
        lat_tab = lat_tab.replace("cline{1-16}", r"hline\hline")
    lat_tab = lat_tab.replace(r"\multirow[t]", r"\multirow")
    lat_tab = lat_tab.replace("bottomrule", "hline")
    lat_tab = lat_tab.replace("mnist_usps", "MNIST/USPS")
    lat_tab = lat_tab.replace("OfficeHomeResnet", "OfficeHome")
    lat_tab = lat_tab.replace("circular_validation", "CircV")
    lat_tab = lat_tab.replace("prediction_entropy", "PE")
    lat_tab = lat_tab.replace("importance_weighted", "IW")
    lat_tab = lat_tab.replace("soft_neighborhood_density", "SND")
    lat_tab = lat_tab.replace("deep_embedded_validation", "DEV")

    # save to txt file
    with open("table_results_all_dataset.txt", "w") as f:
        f.write(lat_tab)


# %%
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate main table for all datasets",
    )

    parser.add_argument(
        "--csv-file",
        type=str,
        help="Path to the csv file containing results for real data",
        default='./readable_csv/results_all_datasets_experiments.csv'
    )

    parser.add_argument(
        "--scorer-selection",
        type=str,
        default="unsupervised"
    )

    args = parser.parse_args()
    df = generate_table(
        args.csv_file, args.csv_file_simulated, args.scorer_selection)
