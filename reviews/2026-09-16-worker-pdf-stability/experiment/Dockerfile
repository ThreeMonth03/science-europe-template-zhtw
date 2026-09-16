FROM datastewardshipwizard/document-worker@sha256:5e5c5e1e436feb49fc4cbcd62c2e0ab2785db2141b0fe40d2926906bcfeaebfc
# Build with the repository root as context, never a private runtime directory.
COPY experiments/markdown-tables/patch_worker.py /tmp/science-europe-patch-worker.py
COPY experiments/worker-pdf-stability/patch_fonts.py /tmp/science-europe-patch-fonts.py
RUN python /tmp/science-europe-patch-worker.py && python /tmp/science-europe-patch-fonts.py
