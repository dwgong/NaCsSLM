import numpy as np
import utils
import slmsuite.hardware.slms.slm
import slmsuite.hardware.cameras.camera
import slmsuite.hardware.cameraslms
import slmsuite.holography.algorithms
import slmsuite.holography.toolbox
import slmsuite.holography.toolbox.phase
import matplotlib.pyplot as plt

# This class acts as an interface between the server and the slmsuite library

class SLMSuiteInterface:
    def __init__(self, server=None):
        """
            Constructor for the interface

            Args:
                server: server that this interface is connected to
            Returns:
                TODO
            Raises:
                TODO
        """
        self.server = server
        self.slm = None 
        self.camera = None
        self.cameraslm = None
        self.hologram = None

    def set_SLM(self, slm=None):
        """
            Sets the SLM for this interface

            Args:
                slm: A SLM object obeying the requirements of the slmusuite abstract slm https://slmsuite.readthedocs.io/en/latest/_autosummary/slmsuite.hardware.slms.html
            Returns:
                TODO
            Raises:
                TODO
        """
        if slm is None:
            # First argument is the slm width in pixels, and second argument is slm length in pixels
            slm = slmsuite.hardware.slms.slm.SLM(1272, 1024)
        self.slm = slm
        if self.camera is not None:
            self.cameraslm = slmsuite.hardware.cameraslms.FourierSLM(self.camera, self.slm)

    def set_camera(self, camera=None):
        """
            Sets the camera for this interface

            Args:
                camera: A camera object obeying the requirements of the slmusuite abstract camera https://slmsuite.readthedocs.io/en/latest/_autosummary/slmsuite.hardware.cameras.camera.html
            Returns:
                TODO
            Raises:
                TODO
        """
        if camera is None:
            camera = slmsuite.hardware.cameras.camera.Camera(1024, 1024)
        self.camera = camera
        if self.slm is not None:
            self.cameraslm = slmsuite.hardware.cameraslms.FourierSLM(self.camera, self.slm)

    def set_slm_amplitude(self, amp):
        """

        """
        self.slm.measured_amplitude = amp
        return 1

    def reset_slm_amplitude(self):
        """

        """
        self.slm.measured_ampitude = None
        return 1

    def get_zernike_phase(self, n, m):
        """

        """
        return slmsuite.holography.toolbox.phase.zernike(self.slm, n, m, aperture="cropped"), 1

    def get_zernike_sum_phase(self, weights):
        """

        """
        return slmsuite.holography.toolbox.phase.zernike_sum(self.slm, weights, aperture="cropped"), 1

    def get_lens_phase(self, focal_length):
        """

        """
        return slmsuite.holography.toolbox.phase.lens(self.slm, focal_length), 1

    def calculate(self, computational_shape, target_spot_array, target_amps=None, n_iters=20, save_options=None, extra_info = None):
        """
            Calculates the required phase pattern

            Args:
                target_spot_array: These are called spot_vectors in the slmsuite documentation. 2 x N array of spots (in camera units) of where we want traps to be.
                target_amps: 1 x N array for the target amplitude of each spot. Does not need to be normalized.
                computational_shape: Shape of computational space for the SLM plane (size 2 tuple). Needs to be bigger than the SLM itself.
                save_options: dict with a set of attributes describing how to save the file. TODO: Describe these. 
                extra_info: TODO
            Returns:
                0 upon success and -1 upon failure
            Raises:
                TODO
        """
        if self.cameraslm is None:
            return None, None, -1
        if self.cameraslm.fourier_calibration is None:
            self.hologram = slmsuite.holography.algorithms.SpotHologram(computational_shape, target_spot_array, spot_amp=target_amps, basis='knm', cameraslm=self.cameraslm)
            no_calib = 1
        else:
            self.hologram = slmsuite.holography.algorithms.SpotHologram(computational_shape, target_spot_array, spot_amp=target_amps, basis='ij', cameraslm=self.cameraslm)
            no_calib = 0
        ntargets = target_spot_array.shape[1]
        if ntargets == 1:
            self.hologram.optimize(method="GS", maxiter=n_iters, feedback='computational_spot')
        else:
            self.hologram.optimize(method="WGS-Kim", maxiter=n_iters, feedback='computational_spot')

        full_path = None
        full_path2 = None
        if save_options is not None:
            full_path, full_path2 = utils.save_slm_calculation(self.hologram, save_options, extra_info)
        if no_calib:
            return full_path, full_path2, 1
        else:
            return full_path, full_path2, 0

    def save_calculation(self, save_options, extra_info=None):
        """

        """
        if self.hologram is None:
            return None, None, -1
        else:
            full_path, full_path2 = utils.save_slm_calculation(self.hologram, save_options, extra_info)
            return full_path, full_path2, 0

    def get_amp(self):
        """
            
        """
        if self.hologram is not None:
            try:
                if isinstance(self.hologram.amp, float):
                    amp = self.hologram.amp
                else:
                    amp = self.hologram.amp.get()
            except:
                amp = self.hologram.amp
            return amp
        else:
            return -1

    def get_phase(self):
        """

        """
        if self.hologram is not None:
            return self.hologram.extract_phase()
        else:
            return -1

    def get_farfield(self, amp=None, phase=None):
        """

        """
        if self.hologram is not None:
            if (amp is None) and (phase is None):
                return self.hologram.extract_farfield(), 0
            elif (amp is None) and (phase is not None):
                amp = self.hologram.amp
            elif (amp is not None) and (phase is None):
                phase = self.hologram.phase
            nearfield = slmsuite.holography.toolbox.pad(amp * np.exp(1j * phase), self.hologram.shape)
            farfield = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(nearfield), norm="ortho"))
            return farfield, 0
        else:
            return None, -1

    def plot_slmplane(self, amp=None, phase=None):
        """

        """
        if self.hologram is not None:
            if (amp is None) and (phase is None):
                self.hologram.plot_nearfield()
                return 0
            elif (amp is None) and (phase is not None):
                amp = self.hologram.amp
            elif (amp is not None) and (phase is None):
                phase = self.hologram.phase
            fig, axs = plt.subplots(1, 2, figsize=(8,4))

            if isinstance(amp, float):
                im_amp = axs[0].imshow(
                    slmsuite.holography.toolbox.pad(
                        amp * np.ones(self.hologram.slm_shape),
                        self.hologram.slm_shape,
                    ),
                    vmin=0,
                    vmax=amp,
                )
            else:
                im_amp = axs[0].imshow(
                    slmsuite.holography.toolbox.pad(amp, self.hologram.slm_shape),
                    vmin=0,
                    vmax=np.amax(amp),
                )

            im_phase = axs[1].imshow(
                slmsuite.holography.toolbox.pad(np.mod(phase, 2*np.pi) / np.pi, self.hologram.slm_shape),
                vmin=0,
                vmax=2,
                interpolation="none",
                cmap="twilight",
            )

            axs[0].set_title("Amplitude")
            axs[1].set_title("Phase")

            for i,ax in enumerate(axs):
                ax.set_xlabel("SLM $x$ [pix]")
                if i==0: ax.set_ylabel("SLM $y$ [pix]")

            fig.tight_layout()
            plt.show()
            return 0
        else:
            return -1

    def plot_farfield(self, amp=None, phase=None):
        """

        """
        if self.hologram is not None:
            if (amp is None) and (phase is None):
                self.hologram.plot_farfield()
            else:
                farfield,_ = self.get_farfield(amp, phase)
                self.hologram.plot_farfield(farfield)
            return 0
        else:
            return -1

    def plot_stats(self):
        """

        """
        if self.hologram is not None:
            self.hologram.plot_stats()
            return 0
        else:
            return -1

    def write_to_SLM(self, phase_pattern):
        """

        """
        if self.cameraslm is None:
            return -1
        else:
            self.cameraslm.slm.write(phase_pattern, settle=True)
