function result = plot_farfield_3d(elem_pos, phases, freq, beam_angle_deg, N, style, resolution, bits)
    % Plot 3D CST-style far-field radiation pattern for RIS
    % Shows RIS array with phase heatmap and 3D beam pattern above it
    %
    % Inputs:
    %   elem_pos       - Element positions (N*N x 3) in meters
    %   phases         - Element phases in radians (N*N x 1) - used for display only
    %   freq           - Frequency in Hz
    %   beam_angle_deg - Beam steering angle (azimuth deflection)
    %   N              - Array size (NxN)
    %   style          - Plot style: 'cst', 'polar3d', 'sphere', 'cartesian'
    %   resolution     - Angular resolution in degrees (default: 2)
    %   bits           - Phase quantization bits (default: 0 = continuous)
    %
    % Outputs:
    %   result - Struct with peak_gain_dB, beam_direction, hpbw

    if nargin < 8 || isempty(bits)
        bits = 0;
    end
    if nargin < 7 || isempty(resolution)
        resolution = 2;
    end
    if nargin < 6 || isempty(style)
        style = 'cst';
    end

    c = 3e8;
    lambda = c / freq;
    k = 2 * pi / lambda;

    % Recompute phases consistently with compute_beam_pattern.m
    % This ensures the far-field pattern matches the beam pattern plot
    x_pos = elem_pos(:,1) - mean(elem_pos(:,1));
    y_pos = elem_pos(:,2) - mean(elem_pos(:,2));

    % Compute steering phases for desired beam angle (azimuth)
    computed_phases = -k * (x_pos * cosd(beam_angle_deg) + y_pos * sind(beam_angle_deg));

    % Apply quantization if specified
    if bits > 0
        num_levels = 2^bits;
        phase_step = 2*pi / num_levels;
        computed_phases = round(computed_phases / phase_step) * phase_step;
    end

    % Use computed phases for pattern calculation (consistent with matlab_beam)
    % Keep original phases for display on RIS surface
    display_phases = phases(:);
    pattern_phases = computed_phases;

    % Compute far-field pattern over hemisphere (upper half only for RIS)
    theta = 0:resolution:90;      % Elevation: 0 to 90 (above array)
    phi = -180:resolution:180;    % Azimuth: full 360

    [THETA, PHI] = meshgrid(theta, phi);

    % Compute wave vectors (spherical to Cartesian)
    % theta = elevation from XY plane, phi = azimuth in XY plane
    kx = k * cosd(THETA) .* cosd(PHI);
    ky = k * cosd(THETA) .* sind(PHI);
    kz = k * sind(THETA);

    % Compute array factor using pattern_phases (consistent with matlab_beam)
    N_elem = size(elem_pos, 1);
    AF = zeros(size(THETA));

    for n = 1:N_elem
        phase_shift = kx * elem_pos(n,1) + ky * elem_pos(n,2) + kz * elem_pos(n,3);
        AF = AF + exp(1j * (pattern_phases(n) + phase_shift));
    end

    % Normalize and convert to dB
    AF_mag = abs(AF);
    AF_max = max(AF_mag(:));

    if AF_max > 0
        AF_norm = AF_mag / AF_max;
        AF_dB = 20 * log10(AF_norm);
    else
        AF_dB = zeros(size(AF_mag));
    end

    % Floor at -30 dB for visualization
    AF_dB_clipped = max(AF_dB, -30);

    % Find peak direction
    [~, idx] = max(AF_dB(:));
    [row, col] = ind2sub(size(AF_dB), idx);
    peak_phi = phi(row);
    peak_theta = theta(col);

    % Compute HPBW
    [~, phi_peak_idx] = min(abs(phi - peak_phi));
    cut_pattern = AF_dB(phi_peak_idx, :);
    above_3dB = cut_pattern >= -3;
    hpbw = sum(above_3dB) * resolution;

    % Get array dimensions for surface plot
    x_elem = elem_pos(:,1);
    y_elem = elem_pos(:,2);
    array_size = max(max(x_elem) - min(x_elem), max(y_elem) - min(y_elem));
    array_center = [mean(x_elem), mean(y_elem), mean(elem_pos(:,3))];

    % Scale factor for beam visualization (beam sits above array)
    beam_scale = array_size * 0.8;
    beam_height_offset = array_size * 0.1;

    % Create figure
    fig = figure('Name', 'RIS Far-Field Pattern (CST Style)', 'NumberTitle', 'off', ...
                 'Position', [50 50 1400 900], 'Color', 'w');

    switch lower(style)
        case 'cst'
            % CST-style: RIS array surface with phase colors + 3D beam on top

            % === MAIN 3D VIEW ===
            ax1 = subplot(2,3,[1,2,4,5]);
            hold on;

            % --- Draw RIS Array Surface with Phase Heatmap ---
            % Use computed phases for display (same as pattern)
            phases_deg = mod(rad2deg(pattern_phases), 360);
            phase_grid = reshape(phases_deg, N, N);

            % Create array surface mesh
            x_grid = reshape(x_elem, N, N);
            y_grid = reshape(y_elem, N, N);
            z_grid = zeros(N, N);

            % Plot RIS surface with phase colors
            surf(x_grid, y_grid, z_grid, phase_grid, ...
                 'FaceColor', 'flat', 'EdgeColor', [0.3 0.3 0.3], ...
                 'LineWidth', 0.3, 'FaceAlpha', 1.0);

            % --- Draw 3D Beam Pattern Above Array ---
            % Convert pattern to 3D coordinates (hemisphere above array)
            R_linear = 10.^(AF_dB_clipped / 20);  % Linear scale
            R_scaled = R_linear * beam_scale;

            % Spherical to Cartesian (beam centered above array)
            X_beam = R_scaled .* cosd(THETA) .* cosd(PHI) + array_center(1);
            Y_beam = R_scaled .* cosd(THETA) .* sind(PHI) + array_center(2);
            Z_beam = R_scaled .* sind(THETA) + beam_height_offset;

            % Plot beam pattern with gain colormap
            h_beam = surf(X_beam, Y_beam, Z_beam, AF_dB_clipped, ...
                         'EdgeColor', 'none', 'FaceAlpha', 0.85);

            % --- Draw Coordinate Axes ---
            axis_len = array_size * 0.7;
            quiver3(array_center(1), array_center(2), 0, axis_len, 0, 0, 0, ...
                    'r', 'LineWidth', 2, 'MaxHeadSize', 0.3);
            quiver3(array_center(1), array_center(2), 0, 0, axis_len, 0, 0, ...
                    'g', 'LineWidth', 2, 'MaxHeadSize', 0.3);
            quiver3(array_center(1), array_center(2), 0, 0, 0, axis_len, 0, ...
                    'b', 'LineWidth', 2, 'MaxHeadSize', 0.3);

            text(array_center(1) + axis_len*1.1, array_center(2), 0, 'X', ...
                 'FontWeight', 'bold', 'Color', 'r', 'FontSize', 12);
            text(array_center(1), array_center(2) + axis_len*1.1, 0, 'Y', ...
                 'FontWeight', 'bold', 'Color', 'g', 'FontSize', 12);
            text(array_center(1), array_center(2), axis_len*1.1, 'Z', ...
                 'FontWeight', 'bold', 'Color', 'b', 'FontSize', 12);

            % --- Draw Reference Circles (Theta/Phi) ---
            % Phi circle (horizontal, around Z axis)
            t_circle = linspace(0, 2*pi, 100);
            r_circle = beam_scale * 0.7;
            plot3(r_circle*cos(t_circle) + array_center(1), ...
                  r_circle*sin(t_circle) + array_center(2), ...
                  zeros(size(t_circle)) + beam_height_offset, ...
                  'g-', 'LineWidth', 1.5);

            % Theta arc (vertical, in XZ plane)
            theta_arc = linspace(0, pi/2, 50);
            plot3(r_circle*cos(theta_arc) + array_center(1), ...
                  zeros(size(theta_arc)) + array_center(2), ...
                  r_circle*sin(theta_arc) + beam_height_offset, ...
                  'r-', 'LineWidth', 1.5);

            % Theta arc (vertical, in YZ plane)
            plot3(zeros(size(theta_arc)) + array_center(1), ...
                  r_circle*cos(theta_arc) + array_center(2), ...
                  r_circle*sin(theta_arc) + beam_height_offset, ...
                  'b-', 'LineWidth', 1.5);

            % --- Mark Peak Beam Direction ---
            peak_r = beam_scale * 1.1;
            peak_x = peak_r * cosd(peak_theta) * cosd(peak_phi) + array_center(1);
            peak_y = peak_r * cosd(peak_theta) * sind(peak_phi) + array_center(2);
            peak_z = peak_r * sind(peak_theta) + beam_height_offset;
            plot3(peak_x, peak_y, peak_z, 'ko', 'MarkerSize', 10, ...
                  'MarkerFaceColor', 'r', 'LineWidth', 2);

            % Draw line from center to peak
            plot3([array_center(1), peak_x], [array_center(2), peak_y], ...
                  [beam_height_offset, peak_z], 'r--', 'LineWidth', 1.5);

            hold off;

            % Axis settings
            axis equal;
            grid on;
            box on;
            xlabel('X (m)', 'FontSize', 11);
            ylabel('Y (m)', 'FontSize', 11);
            zlabel('Z (m)', 'FontSize', 11);
            title(sprintf('RIS %dx%d Far-Field @ %.2f GHz\nBeam Deflection: %.1f°', ...
                  N, N, freq/1e9, beam_angle_deg), 'FontSize', 13);
            view(135, 30);

            % Add colorbars
            % Beam pattern colorbar (dBi)
            cb1 = colorbar('eastoutside');
            cb1.Label.String = 'Gain (dB)';
            cb1.Label.FontSize = 10;
            colormap(ax1, jet(256));
            caxis([-30 0]);

            % === PHASE HEATMAP (top-down view) ===
            ax2 = subplot(2,3,3);
            imagesc(x_grid(1,:), y_grid(:,1), phase_grid);
            colormap(ax2, hsv(256));
            cb2 = colorbar;
            cb2.Label.String = 'Phase (°)';
            caxis([0 360]);
            axis equal tight;
            xlabel('X (m)');
            ylabel('Y (m)');
            title(sprintf('Phase Distribution\n(%d-element array)', N*N), 'FontSize', 11);
            set(gca, 'YDir', 'normal');

            % === POLAR PATTERN CUT ===
            subplot(2,3,6);
            % Azimuth cut at theta = peak_theta
            [~, theta_peak_idx] = min(abs(theta - peak_theta));
            az_cut_dB = AF_dB_clipped(:, theta_peak_idx);
            az_cut_linear = 10.^(az_cut_dB / 20);

            polarplot(deg2rad(phi), az_cut_linear, 'b-', 'LineWidth', 2);
            hold on;
            polarplot(deg2rad([peak_phi peak_phi]), [0 1], 'r--', 'LineWidth', 1.5);
            hold off;

            pax = gca;  % Get PolarAxes after polarplot
            pax.ThetaZeroLocation = 'right';
            pax.ThetaDir = 'counterclockwise';
            pax.RLim = [0 1.1];
            pax.RTick = [0.1 0.25 0.5 0.71 1.0];
            pax.RTickLabel = {'-20', '-12', '-6', '-3', '0 dB'};
            title(sprintf('Azimuth Cut (\\theta=%.0f°)', peak_theta), 'FontSize', 11);

        case 'polar3d'
            % Original polar3d style (kept for compatibility)
            R = (AF_dB_clipped + 30) / 30;
            R = max(R, 0);

            X = R .* cosd(THETA) .* cosd(PHI);
            Y = R .* cosd(THETA) .* sind(PHI);
            Z = R .* sind(THETA);

            ax1 = subplot(2,2,[1,3]);
            surf(X, Y, Z, AF_dB_clipped, 'EdgeColor', 'none', 'FaceAlpha', 0.9);
            hold on;

            % Reference sphere
            [Xs, Ys, Zs] = sphere(50);
            Zs(Zs < 0) = 0;  % Upper hemisphere only
            ref_r = 0.5;
            surf(ref_r*Xs, ref_r*Ys, ref_r*Zs, 'FaceColor', [0.8 0.8 0.8], ...
                 'EdgeColor', 'none', 'FaceAlpha', 0.1);

            % Coordinate axes
            line([0 1.2], [0 0], [0 0], 'Color', 'r', 'LineWidth', 1.5);
            line([0 0], [0 1.2], [0 0], 'Color', 'g', 'LineWidth', 1.5);
            line([0 0], [0 0], [0 1.2], 'Color', 'b', 'LineWidth', 1.5);
            text(1.25, 0, 0, 'X', 'FontWeight', 'bold', 'Color', 'r');
            text(0, 1.25, 0, 'Y', 'FontWeight', 'bold', 'Color', 'g');
            text(0, 0, 1.25, 'Z', 'FontWeight', 'bold', 'Color', 'b');

            colormap(ax1, jet(256));
            cb = colorbar;
            cb.Label.String = 'Gain (dB)';
            caxis([-30 0]);
            axis equal;
            grid on;
            xlabel('X'); ylabel('Y'); zlabel('Z');
            title(sprintf('3D Far-Field\nDeflection: %.1f°', beam_angle_deg));
            view(135, 25);
            hold off;

            % Cuts
            subplot(2,2,2);
            [~, theta_zero_idx] = min(abs(theta));
            az_cut = AF_dB_clipped(:, theta_zero_idx);
            polarplot(deg2rad(phi), az_cut + 30, 'b-', 'LineWidth', 2);
            pax2 = gca;
            pax2.RLim = [0 30];
            pax2.RTick = [0 10 20 30];
            pax2.RTickLabel = {'-30', '-20', '-10', '0'};
            title('Azimuth Cut');

            subplot(2,2,4);
            [~, phi_peak_idx] = min(abs(phi - peak_phi));
            el_cut = AF_dB_clipped(phi_peak_idx, :);
            polarplot(deg2rad(theta), el_cut + 30, 'r-', 'LineWidth', 2);
            pax3 = gca;
            pax3.RLim = [0 30];
            pax3.ThetaZeroLocation = 'top';
            pax3.RTick = [0 10 20 30];
            pax3.RTickLabel = {'-30', '-20', '-10', '0'};
            title(sprintf('Elevation Cut (\\phi=%.0f°)', peak_phi));

        case 'sphere'
            % Map onto sphere surface
            [Xs, Ys, Zs] = sphere(90);
            Zs(Zs < 0) = NaN;  % Upper hemisphere only

            % Interpolate pattern onto sphere
            sphere_theta = asind(Zs);
            sphere_phi = atan2d(Ys, Xs);
            AF_interp = interp2(theta, phi', AF_dB_clipped, sphere_theta, sphere_phi, 'linear', -30);

            surf(Xs, Ys, Zs, AF_interp, 'EdgeColor', 'none', 'FaceAlpha', 0.95);
            colormap(jet(256));
            colorbar;
            caxis([-30 0]);
            axis equal;
            grid on;
            xlabel('X'); ylabel('Y'); zlabel('Z');
            title(sprintf('Far-Field (Sphere)\nDeflection: %.1f°', beam_angle_deg));
            view(135, 25);

        case 'cartesian'
            subplot(1,2,1);
            surf(THETA, PHI, AF_dB_clipped, 'EdgeColor', 'none');
            colormap(jet(256));
            colorbar;
            caxis([-30 0]);
            xlabel('Elevation \theta (°)');
            ylabel('Azimuth \phi (°)');
            zlabel('Gain (dB)');
            title('3D Pattern');
            view(45, 30);

            subplot(1,2,2);
            imagesc(theta, phi, AF_dB_clipped);
            colormap(jet(256));
            colorbar;
            caxis([-30 0]);
            xlabel('Elevation \theta (°)');
            ylabel('Azimuth \phi (°)');
            title('2D Pattern');
            axis xy;
    end

    % Return metrics
    result.peak_gain_dB = 0;
    result.peak_theta = peak_theta;
    result.peak_phi = peak_phi;
    result.hpbw = hpbw;
    result.array_size = N;
end
