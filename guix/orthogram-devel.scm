(define-module (guix orthogram-devel)
  ;;
  #:use-module (guix build-system python)
  #:use-module (guix download)
  #:use-module (guix gexp)
  #:use-module (guix git-download)
  #:use-module (guix packages)
  #:use-module (guix utils)
  ;;
  #:use-module ((guix licenses) #:prefix license:)
  ;;
  #:use-module (gnu packages base)
  #:use-module (gnu packages python)
  #:use-module (gnu packages python-check)
  #:use-module (gnu packages python-xyz)
  #:use-module (gnu packages sphinx)
  #:use-module (gnu packages version-control)
  ;;
  #:use-module (guix orthogram))

(define-public python-types-pyyaml
  (package
   (name "python-types-pyyaml")
   (version "6.0.12.12")
   (source
    (origin
     (method url-fetch)
     (uri (pypi-uri "types-PyYAML" version))
     (sha256
      (base32 "0qjhhphqjql5xf9lbcb7472i1yl531kg3hzmbbwzvq7xjb9p6hrk"))))
   (build-system python-build-system)
   (home-page "https://github.com/python/typeshed")
   (synopsis "Typing stubs for PyYAML")
   (description
    "This is a PEP 561 type stub package for the PyYAML package.  It can be
used by type-checking tools like mypy, pyright, pytype, PyCharm,
etc. to check code that uses PyYAML.")
   (license (list license:asl2.0))))

(define vcs-file?
  ;; Return true if the given file is under version control.
  (or (git-predicate (current-source-directory))
      (const #t)))

(define-public python-orthogram-devel
  (package
   (inherit python-orthogram)
   (name "python-orthogram-devel")
   (version "0.8.2")
   (source (local-file "." "python-orthogram-checkout"
                       #:recursive? #t
                       #:select? vcs-file?))
   (propagated-inputs
    (modify-inputs (package-propagated-inputs python-orthogram)
		   (prepend git
			    `(,git "gui")
			    gnu-make
			    poetry
			    python
			    python-docutils
			    python-mypy
			    python-sphinx
			    python-sphinx-rtd-theme
			    python-types-pyyaml)))
   (synopsis "Development environment for @code{python-orthogram}")))
