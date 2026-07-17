import multiprocessing

from otklik_backend.api.app import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
