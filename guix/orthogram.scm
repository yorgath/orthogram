(define-module (guix orthogram)
  ;;
  #:use-module (guix build-system pyproject)
  #:use-module (guix build-system python)
  #:use-module (guix download)
  #:use-module (guix packages)
  ;;
  #:use-module ((guix licenses) #:prefix license:)
  ;;
  #:use-module (gnu packages gtk)
  #:use-module (gnu packages python-build)
  #:use-module (gnu packages python-xyz))

(define-public python-cassowary
  (package
   (name "python-cassowary")
   (version "0.5.2")
   (source
    (origin
     (method url-fetch)
     (uri (pypi-uri "cassowary" version))
     (sha256
      (base32 "1p86sjisl41w346ivdvimm7zmzc0lpqzdj1rv4ycm3kk483x3h6p"))))
   (build-system python-build-system)
   (home-page "https://brodderick.com/projects/cassowary")
   (synopsis
    "Python implementation of the Cassowary constraint solving algorithm")
   (description
    "A pure Python implementation of the Cassowary constraint-solving
algorithm.  Cassowary is the algorithm that forms the core of the OS X
and iOS visual layout mechanism.")
   (license (list license:bsd-3 license:asl2.0))))

(define-public python-orthogram
  (package
   (name "python-orthogram")
   (version "0.8.2")
   (source
    (origin
     (method url-fetch)
     (uri (pypi-uri "orthogram" version))
     (sha256
      (base32 "1xzs437dw4agrl3z8djhhhwmd4ysjp6dfqvdakk03v1qbrfg4l11"))))
   (build-system pyproject-build-system)
   ;; All tests are visual, unfortunately.
   (arguments
    '(#:tests? #f))
   (native-inputs
    (list python-poetry-core))
   (propagated-inputs
    (list
     python-cassowary
     python-networkx
     python-pycairo
     python-pyyaml
     python-shapely))
   (home-page "https://github.com/yorgath/orthogram")
   (synopsis "Draw block diagrams")
   (description
    "Orthogram is a command line program and Python library that lets
you draw block diagrams.  It reads the definition of a diagram from a
YAML file and produces a PNG file.")
   (license license:gpl3+)))
