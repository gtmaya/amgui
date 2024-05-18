import abc
import ctypes
import os.path
import pathlib
import tempfile
import typing as typ
import uuid

# noinspection PyPep8Naming
import OpenGL.GL as gl
import PIL.Image as Image
import glfw
import imgui
from imgui.integrations.glfw import GlfwRenderer

from . import constants as c

if typ.TYPE_CHECKING:
    # noinspection PyProtectedMember,PyUnresolvedReferences,SpellCheckingInspection
    import glfw._GLFWwindow as GLFWwindow


class Icon(object):

    def __init__(self, ordered_icon_paths: typ.Iterable[str]):
        self._images = []

        for icon_path in ordered_icon_paths:
            self._images.append(Image.open(icon_path))

    @property
    def glfw_images(self):
        return self._images


class Window(abc.ABC):

    _WINDOW_TITLE: str = ''
    _WINDOW_WIDTH: int = 1280
    _WINDOW_HEIGHT: int = 720
    _WINDOW_ICON: Icon = None
    _WINDOW_ID_UNIQUE: str = str(uuid.uuid4())
    _WINDOW_ID_PERSISTENT: str = 'default'
    _GROUP_UNIQUE_WINDOWS_IN_TASKBAR: bool = True

    _IMGUI_USE_INI: bool = True
    _IMGUI_INI_DIR: pathlib.Path = pathlib.Path(tempfile.gettempdir(), 'amgui')

    # -- Not sure if macOS is still this far behind - probably!
    _GLFW_CONTEXT_VERSION_MAJOR: int = 3
    _GLFW_CONTEXT_VERSION_MINOR: int = 3
    _GLFW_OPENGL_PROFILE: int = glfw.OPENGL_CORE_PROFILE
    _GL_CLEAR_COLOUR: tuple[int, int, int, int] = (0, 0, 0, 1)

    def __init__(self):
        self._pre_init()

        super().__init__()
        self._window, self._renderer = self._init_glfw()

        glfw.set_window_refresh_callback(self.window, self._resize_event)

        self._post_init()
        self._glfw_loop()

    def _pre_init(self, *args, **kwargs) -> None:
        """
        Override this method to be called before initialisation of GLFW/imgui.
        """
        pass

    def _post_init(self, *args, **kwargs) -> None:
        """
        Override this method to be called after initialisation of GLFW/imgui.
        """
        pass

    def _pre_exit_loop(self) -> None:
        """
        Override this method to be called before GLFW/imgui cleans up.  Default invokes imgui .ini saving.
        """
        imgui.save_ini_settings_to_disk(self._imgui_ini_path())

    def _post_exit_loop(self) -> None:
        """
        Override this method to be called after GLFW/imgui cleans up.
        """
        pass

    @classmethod
    def _imgui_ini_path(cls) -> str:
        """
        Convenience getter for imgui .ini path.
        :return: Path of imgui .ini file.
        """
        return str(cls._IMGUI_INI_DIR / f'{cls._WINDOW_ID_PERSISTENT}.ini')

    @classmethod
    def _init_glfw(cls) -> tuple['GLFWwindow', GlfwRenderer]:
        """
        Initialises GLFW.
        """

        if not glfw.init():
            c.logger.critical('Could not initialize OpenGL context')
            exit(1)

        if cls._GROUP_UNIQUE_WINDOWS_IN_TASKBAR:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(str(cls._WINDOW_ID_PERSISTENT))
        else:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(str(cls._WINDOW_ID_UNIQUE))

        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, cls._GLFW_CONTEXT_VERSION_MAJOR)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, cls._GLFW_CONTEXT_VERSION_MINOR)
        glfw.window_hint(glfw.OPENGL_PROFILE, cls._GLFW_OPENGL_PROFILE)

        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, gl.GL_TRUE)

        # Create a windowed mode window and its OpenGL context
        window = glfw.create_window(int(cls._WINDOW_WIDTH), int(cls._WINDOW_HEIGHT), cls._WINDOW_TITLE, None, None)
        glfw.make_context_current(window)

        if cls._WINDOW_ICON is not None:
            images = cls._WINDOW_ICON.glfw_images
            glfw.set_window_icon(window, len(images), images)

        if not window:
            glfw.terminate()
            c.logger.critical('Could not initialize Window')
            exit(1)

        imgui.create_context()

        os.makedirs(cls._IMGUI_INI_DIR, exist_ok=True)

        if cls._IMGUI_USE_INI:
            ini_path = cls._imgui_ini_path()
            print(ini_path, type(ini_path))
            imgui.get_io().ini_file_name = ini_path
            imgui.load_ini_settings_from_disk(ini_path)
        else:
            imgui.get_io().ini_file_name = None

        renderer = GlfwRenderer(window)
        gl.glClearColor(*cls._GL_CLEAR_COLOUR)

        return window, renderer

    @property
    def size(self) -> tuple[int, int]:
        return glfw.get_window_size(self.window)

    # noinspection PyUnusedLocal
    def _resize_event(self, window: 'GLFWwindow', *args, **kwargs) -> None:
        self._draw()

    @property
    def window(self) -> 'GLFWwindow':
        return self._window

    @property
    def renderer(self) -> GlfwRenderer:
        return self._renderer

    def _draw(self) -> None:
        imgui.new_frame()

        self.draw()

        gl.glClearColor(*self._GL_CLEAR_COLOUR)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        imgui.render()

        try:
            self._renderer.render(imgui.get_draw_data())
        except AttributeError:
            pass

        glfw.swap_buffers(self.window)

    @abc.abstractmethod
    def draw(self) -> None:
        pass

    def _glfw_loop(self) -> None:
        while not glfw.window_should_close(self.window):
            glfw.poll_events()
            self._renderer.process_inputs()
            if imgui.get_io().want_save_ini_settings:
                print('wants to save!')
            self._draw()

        self._pre_exit_loop()
        self._renderer.shutdown()
        glfw.terminate()
