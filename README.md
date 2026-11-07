# This repository has moved

**Team Foursight's code is in our main repository:
<https://github.com/AsJayTee/DSA4262-Foursight>**

Everything needed to run our m6A prediction script is there: installation
instructions, the trained model, a test dataset, and a Google Colab notebook.
Start with that repository's README.

## Why this repository existed

During the code review, this repository held a prediction-only copy of our
code. We used it to keep our Task 2 visualisation dashboard private until the
final submission, as requested by the course teaching team.

That was not possible within the main repository. The dashboard's source code
was part of it, and the dashboard itself was hosted on GitHub Pages from that
same repository. Hiding the code meant making the main repository private, and
making it private also took the hosted dashboard offline. Reviewers therefore
needed a separate public repository to run the prediction script in the
meantime.

## Is the code the same?

Yes. The prediction script, the package it uses, the trained model and the
test dataset in this copy were byte-for-byte identical to the main repository's,
and none of them has changed since. Anyone who reviewed the code here ran
exactly the code that is in the main repository. The copy remains viewable in
this repository's commit history.
