# Foursight — m6A RNA modification prediction

Predicting N6-methyladenosine (m6A) RNA modifications from Nanopore direct
RNA-seq data, for DSA4262 (NUS / Genome Institute of Singapore).

The input is the m6Anet-processed `data.json`: for each candidate site (a
position on a transcript at a DRACH motif), the signal features of every read
aligned there. The output is a CSV with one score per site; a higher score
means the site is more likely to carry m6A.

> **About this repository.** This is a prediction-only copy of our project
> repository, made for the code review. It holds everything needed to run the
> prediction script: the code, the trained model and a test dataset. Our main
> repository also contains our Task 2 visualisation platform, which has not
> been submitted yet, so that repository is private for now. It will be made
> public with our final submission, and this copy will then be retired.
> The code is identical to the main repository's, so some comments mention
> files that are not part of this copy, such as the training scripts and our
> design notes.

---

## Running the prediction script

Choose **one** of the two options below. Neither needs a GPU or any
credentials, and both use a 1,000-site test dataset included in this
repository.

### Option A: Google Colab (no setup)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AsJayTee/DSA4262-Foursight-Inference/blob/main/predict_colab.ipynb)

Open the notebook and choose **Runtime → Run all**. It clones this repository,
installs it, runs the prediction script on the test dataset, checks the output
format and displays the predictions. This takes about a minute.

### Option B: your own machine (Ubuntu)

Requires Python 3.10 or newer and git. On a fresh AWS Ubuntu instance, install
them first (Ubuntu does not include `venv` by default):

```bash
sudo apt-get update && sudo apt-get install -y git python3-venv python3-pip
```

Then:

```bash
git clone https://github.com/AsJayTee/DSA4262-Foursight-Inference.git
cd DSA4262-Foursight-Inference

python3 -m venv .venv
source .venv/bin/activate
pip install .

python scripts/predict.py \
    --model models/final \
    --input data/sample/sample.json.gz \
    --output predictions.csv
```

Expected output (the time varies by machine):

```
1,000 sites scored -> predictions.csv  (2.1s, model=site_graph_ensemble)
```

`pip install .` installs three packages (numpy, pandas and scikit-learn). The
model itself runs in plain numpy, so torch is not needed.

<details>
<summary>On macOS or Windows</summary>

The same commands work on macOS. On Windows, activate the environment with
`.venv\Scripts\activate` instead of `source .venv/bin/activate`, and use
`python` instead of `python3`.

</details>

### Checking the output

```bash
python -c "from m6a.evaluation import validate_submission; problems = validate_submission('predictions.csv', 'data/sample/sample.json.gz'); print(chr(10).join(problems) or 'OK: predictions.csv has the required format and one row per input site')"
```

This prints `OK` if the columns are exactly
`transcript_id,transcript_position,score`, every score is a number in [0, 1],
and the CSV has exactly one row for every site in the input file. Otherwise, it
lists each problem.

The first rows of `predictions.csv` look like this:

```csv
transcript_id,transcript_position,score
ENST00000000412,769,0.22266666666666665
ENST00000000412,2195,0.309
```

`transcript_id` and `transcript_position` are copied from the input. `score` is
each site's rank within the file, averaged over the six networks of the
ensemble and scaled to [0, 1]. It orders sites by how likely they are to be
modified, but it is **not a calibrated probability**: do not count modified
sites by applying a threshold to it.

The test dataset shows that the code runs; it does not measure accuracy. Its
sites are taken from the training data, and its 1,000 sites are spread over
884 transcripts, so few of them have the neighbouring sites the model uses. See
[Results](#results) for held-out performance.

### Running the tests

```bash
pip install ".[dev]"
python -m pytest -q
```

The tests run the prediction script on the test dataset and check its output,
and check that the script needs nothing beyond the three packages above.

### Predicting on other data

`--input` accepts any `data.json` or `data.json.gz` in the m6Anet-processed
format. For example, to predict on one full SG-NEx sample from the public
[SG-NEx bucket](https://registry.opendata.aws/sgnex/), which needs no
credentials:

```bash
curl -o sgnex.json https://sg-nex-data.s3.amazonaws.com/data/processed_data/m6Anet/SGNex_Hct116_directRNA_replicate3_run4/data.json
python scripts/predict.py --model models/final --input sgnex.json --output sgnex_predictions.csv
```

The file is 1.5 GB and holds 1,302,514 sites. On an 8-core laptop, prediction
took about 5 minutes and used 5.6 GB of memory at its peak, so use a machine
with at least 8 GB of RAM. Expect it to take longer on fewer cores.

---

## The method

The shipped model is an ensemble of three graph-network designs, trained with
two random seeds each (six networks). Every design starts the same way: a
DeepSets encoder summarises each site's reads into a vector and an "own-reads"
score. Each read is one RNA molecule, so a site's reads are a set of
independent measurements. The designs then differ in how they use the other
candidate sites on the same transcript (its *neighbours*):

- **Two-head H2GCN:** an H2GCN-style graph network (Zhu et al., NeurIPS 2020)
  that keeps a site's own evidence separate from its neighbours'. It has one
  output per labelled cell line and ships their mean.
- **Residual + dropout (`res_gate`):** the site's own-reads score, plus a
  correction from its neighbours within 150 nt, weighted by distance.
- **Scalar messages + dropout (`scalar_drop`):** each neighbour passes a single
  number, its own-reads score, which corroborates or contradicts the site.

The last two were trained with neighbours randomly removed, so they do not
depend on any single neighbour; this is what lets them transfer to a cell line
they were not trained on. The model was trained on both labelled releases
(HCT116 and HEK293T).

---

## Results

Held-out performance from 5-fold cross-validation **grouped by gene**, so that
no gene appears in both training and validation, with all models trained on
both cell lines:

| Model | HCT116 PR AUC | HCT116 ROC AUC | HEK293T PR AUC | HEK293T ROC AUC |
|---|---:|---:|---:|---:|
| Random classifier | 0.045 | 0.500 | 0.072 | 0.500 |
| Simple baseline (logistic regression) | 0.415 | 0.899 | 0.331 | 0.813 |
| Quantiles + LightGBM | 0.472 | 0.918 | 0.392 | 0.829 |
| m6Anet (pretrained on HCT116) | 0.503\* | 0.932\* | 0.356 | 0.819 |
| DeepSet (reads only, no neighbours) | 0.541 | 0.936 | 0.429 | 0.840 |
| **Final model** | **0.607** | **0.958** | **0.460** | **0.865** |

\* Not held out: m6Anet was trained on HCT116 data.

Only 4.5% (HCT116) and 7.2% (HEK293T) of sites are modified, so PR AUC is the
more informative metric; ROC AUC is high for every model.

Performance depends strongly on read depth (the number of RNA molecules
measured at a site). Every training site has at least 20 reads, while SG-NEx
sites have a median of 3. With each site's reads randomly thinned, the final
model's PR AUC falls as follows:

| PR AUC | 1 read | 3 reads | 10 reads | All (≥ 20) |
|---|---:|---:|---:|---:|
| Final model, HCT116 | 0.333 | 0.451 | 0.534 | 0.607 |
| Final model, HEK293T | 0.279 | 0.341 | 0.397 | 0.460 |

The full comparison, significance tests and limitations are in the report.

---

## Repository layout

```
scripts/predict.py    the prediction script
src/m6a/              the package
  data.py             reading the signal JSON
  models/site_graph.py  the shipped ensemble, scored in numpy
  registry.py         name -> model lookup
  evaluation.py       the output-format check
models/final/         the trained model (six networks, .npz weights)
data/sample/          the 1,000-site test dataset
predict_colab.ipynb   the Colab notebook (Option A)
tests/                tests of the prediction script
```

---

## License and attribution

Coursework for DSA4262, National University of Singapore. The SG-NEx data is
described in Chen et al., *Nature Methods* 22, 801–812 (2025). m6Anet is
described in Hendra et al., *Nature Methods* 19, 1590–1598 (2022). H2GCN is
described in Zhu et al., *NeurIPS* 33 (2020).
