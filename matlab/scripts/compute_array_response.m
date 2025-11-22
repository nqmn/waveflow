function [theta, phi, AF_dB] = compute_array_response(elem_pos, phases, freq, theta_range, phi_range, resolution)
    % Compute array factor for RIS over 2D angular space
    %
    % Inputs:
    %   elem_pos    - Element positions (N*N x 3) in meters
    %   phases      - Element phases in radians (N*N x 1)
    %   freq        - Frequency in Hz
    %   theta_range - [min, max] elevation angles (degrees)
    %   phi_range   - [min, max] azimuth angles (degrees)
    %   resolution  - Angular resolution (degrees)
    %
    % Outputs:
    %   theta  - Elevation angles vector (degrees)
    %   phi    - Azimuth angles vector (degrees)
    %   AF_dB  - Array factor in dB (2D matrix, size: len(phi) x len(theta))

    c = 3e8;
    lambda = c / freq;
    k = 2 * pi / lambda;

    % Create angle grids
    theta = theta_range(1):resolution:theta_range(2);
    phi = phi_range(1):resolution:phi_range(2);

    [THETA, PHI] = meshgrid(theta, phi);

    % Compute wave vectors for each direction
    % Using spherical coordinates:
    %   theta = elevation from XY plane
    %   phi = azimuth in XY plane
    kx = k * cosd(THETA) .* cosd(PHI);
    ky = k * cosd(THETA) .* sind(PHI);
    kz = k * sind(THETA);

    % Compute array factor
    N_elem = size(elem_pos, 1);
    AF = zeros(size(THETA));

    % Reshape phases to column vector
    phases = phases(:);

    for n = 1:N_elem
        % Phase shift due to element position
        phase_shift = kx * elem_pos(n,1) + ky * elem_pos(n,2) + kz * elem_pos(n,3);
        % Add element contribution with its programmed phase
        AF = AF + exp(1j * (phases(n) + phase_shift));
    end

    % Convert to dB (normalized to peak)
    AF_mag = abs(AF);
    AF_max = max(AF_mag(:));
    if AF_max > 0
        AF_dB = 20 * log10(AF_mag / AF_max);
    else
        AF_dB = zeros(size(AF_mag));
    end
    AF_dB(AF_dB < -40) = -40;  % Floor at -40 dB

    % Optional: create visualization
    figure('Name', 'Array Response', 'NumberTitle', 'off');

    subplot(1,2,1);
    imagesc(theta, phi, AF_dB);
    xlabel('Theta (elevation, deg)');
    ylabel('Phi (azimuth, deg)');
    title('Array Factor (dB)');
    colorbar;
    caxis([-40 0]);
    axis xy;

    subplot(1,2,2);
    surf(THETA, PHI, AF_dB, 'EdgeColor', 'none');
    xlabel('Theta (deg)');
    ylabel('Phi (deg)');
    zlabel('AF (dB)');
    title('3D Array Factor');
    colorbar;
    view(45, 30);
end
