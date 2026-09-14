"""Application coordinator and lifecycle manager for Robex."""

import logging

from robex.core.safety import global_safety
from robex.core.input_driver import driver
from robex.vision.screen import screen_grabber
from robex.gui.main_window import MainWindow

logger = logging.getLogger("robex")


def setup_logging():
    """Initializes logging formatting for stdout and debugging."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%H:%M:%S"
    )


class RobexApp:
    """Manages Robex lifecycle: startup, hotkey registration, UI, and clean shutdown."""

    def __init__(self):
        setup_logging()
        logger.info("Initializing Robex...")

    def run(self):
        """Starts background listeners and presents the desktop GUI."""
        # Start global F12 killswitch listener
        global_safety.start_listener()

        try:
            window = MainWindow()
            window.run()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received.")
        finally:
            self.shutdown()

    def shutdown(self):
        """Performs clean shutdown releasing all resources and inputs."""
        logger.info("Shutting down Robex...")
        global_safety.stop_listener()
        driver.release_all()
        screen_grabber.close()
        logger.info("Robex shutdown cleanly.")


def main():
    """Entry point function."""
    app = RobexApp()
    app.run()


if __name__ == "__main__":
    main()
