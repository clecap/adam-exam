FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
     bash              \
     ca-certificates   \
     poppler-utils     \
     libzbar0          \
     libgl1            \
     libglib2.0-0      \
     libedit2          \
     tesseract-ocr     \
     tesseract-ocr-eng \
     libtesseract-dev  \
     libleptonica-dev  \
     ghostscript       \
     qpdf              \
     parallel          \
  && rm -rf /var/lib/apt/lists/*
    
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir \
     pymupdf \
     pypdfium2 \
     opencv-python \
     reportlab \
     pyzbar \
     numpy \
     openpyxl \
     pdf2image \
     pillow \
     pypdf \
     pytesseract \
     pikepdf \
     img2pdf \
 &&    ln -sf /bin/bash /bin/sh 
     
WORKDIR /app

RUN chsh -s /bin/bash root
SHELL ["/bin/bash", "-c"]
CMD ["bash", "-lc", "tail -f /dev/null"]
