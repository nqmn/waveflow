%% Standalone RIS Beam Pattern Visualization
% This script runs independently in MATLAB without RISNet
% Computes and plots 3D far-field radiation pattern for a phased array RIS

clear all; close all; clc;

%% RIS Parameters
N = 16;                          % Array size: 16x16 elements
freq = 5.8e9;                    % Frequency: 5.8 GHz
c = 3e8;                         % Speed of light
lambda = c / freq;               % Wavelength
k = 2 * pi / lambda;             % Wavenumber

% Element spacing (lambda/2 is standard)
spacing = lambda / 2;

% Beam steering angle in degrees (0 = broadside, +45 = steer 45 degrees)
beam_angle_deg = 45;

% Quantization: 0 = continuous, 1 = 1-bit, 2 = 2-bit, 3 = 3-bit, etc.
bits = 1;

%% Generate Element Positions
% Create a uniform planar array (UPA) centered at origin
[row, col] = meshgrid(0:N-1, 0:N-1);
x_elem = (row(:) - (N-1)/2) * spacing;
y_elem = (col(:) - (N-1)/2) * spacing;
z_elem = zeros(size(x_elem));

elem_pos = [x_elem, y_elem, z_elem];

fprintf('\n========================================\n');
fprintf('RIS Beam Pattern Analysis\n');
fprintf('========================================\n');
fprintf('Array size:        %dx%d (%d elements)\n', N, N, N*N);
fprintf('Frequency:         %.2f GHz\n', freq/1e9);
fprintf('Wavelength:        %.4f m\n', lambda);
fprintf('Element spacing:   %.4f m (λ/%.2f)\n', spacing, lambda/spacing);
fprintf('Beam angle:        %.1f°\n', beam_angle_deg);
fprintf('Quantization:      %d-bit\n', bits);
fprintf('========================================\n\n');

%% Compute Steering Phases
% Linear phase gradient for beam steering
phases = -k * (x_elem * cosd(beam_angle_deg) + y_elem * sind(beam_angle_deg));

% Apply quantization if specified
if bits > 0
    num_levels = 2^bits;
    phase_step = 2*pi / num_levels;
    phases = round(phases / phase_step) * phase_step;
    fprintf('Quantization levels: %d\n', num_levels);
    fprintf('Phase step:          %.1f°\n', phase_step * 180/pi);
else
    fprintf('Using continuous (unquantized) phases\n');
end

%% Compute 1D Beam Pattern (Azimuth Cut)
fprintf('\nComputing 1D beam pattern...\n');
angles_1d = -90:0.5:90;
pattern_1d = zeros(size(angles_1d));

for idx = 1:length(angles_1d)
    ang = angles_1d(idx);
    kx = k * cosd(ang);
    ky = k * sind(ang);
    steering = kx * x_elem + ky * y_elem;
    pattern_1d(idx) = abs(sum(exp(1j * (phases + steering))));
end

% Normalize to dB
pattern_1d_max = max(pattern_1d);
pattern_1d_dB = 20 * log10(pattern_1d / pattern_1d_max + 1e-10);
pattern_1d_dB = max(pattern_1d_dB, -40);  % Floor at -40 dB

%% Compute 3D Far-Field Pattern (Hemisphere)
fprintf('Computing 3D far-field pattern...\n');
theta = 0:2:90;      % Elevation: 0 to 90 degrees
phi = -180:2:180;    % Azimuth: -180 to 180 degrees

[THETA, PHI] = meshgrid(theta, phi);

% Compute array factor over 2D angular grid
AF = zeros(size(THETA));

for n = 1:length(x_elem)
    % Wave vector for each element
    phase_shift = k * (x_elem(n) * cosd(THETA) .* cosd(PHI) + ...
                       y_elem(n) * cosd(THETA) .* sind(PHI) + ...
                       z_elem(n) * sind(THETA));

    AF = AF + exp(1j * (phases(n) + phase_shift));
end

% Convert to dB
AF_mag = abs(AF);
AF_max = max(AF_mag(:));
AF_dB = 20 * log10(AF_mag / AF_max + 1e-10);
AF_dB = max(AF_dB, -30);  % Floor at -30 dB

% Find peak direction
[~, idx] = max(AF_dB(:));
[row_peak, col_peak] = ind2sub(size(AF_dB), idx);
peak_phi = phi(row_peak);
peak_theta = theta(col_peak);

fprintf('Peak direction:    theta=%.1f°, phi=%.1f°\n', peak_theta, peak_phi);

%% Compute Metrics
% Main lobe width (-3 dB beamwidth)
above_3dB = pattern_1d_dB >= -3;
main_lobe_indices = find(above_3dB);
if ~isempty(main_lobe_indices)
    main_lobe_width = (main_lobe_indices(end) - main_lobe_indices(1)) * 0.5;
else
    main_lobe_width = 0;
end

% Sidelobe level
peak_idx = find(pattern_1d_dB == max(pattern_1d_dB), 1);
sidelobe_region_1 = pattern_1d_dB(1:max(1, peak_idx-10));
sidelobe_region_2 = pattern_1d_dB(min(length(pattern_1d_dB), peak_idx+10):end);
sidelobe_level = max([sidelobe_region_1, sidelobe_region_2]);

fprintf('\nBeam Metrics:\n');
fprintf('  Main lobe width (-3dB):  %.1f°\n', main_lobe_width);
fprintf('  Sidelobe level:          %.1f dB\n', sidelobe_level);

%% Create Visualization Figure
fprintf('\nGenerating plots...\n');

fig = figure('Name', sprintf('RIS Beam Pattern - %.1f° Steering', beam_angle_deg), ...
             'NumberTitle', 'off', 'Position', [100 100 1400 900]);

%% Plot 1: 1D Beam Pattern (Cartesian)
subplot(2,3,1);
plot(angles_1d, pattern_1d_dB, 'b-', 'LineWidth', 2);
hold on;
plot(beam_angle_deg, max(pattern_1d_dB)-3, 'ro', 'MarkerSize', 8, 'MarkerFaceColor', 'r');
yline(-3, 'g--', 'LineWidth', 1.5);
hold off;
grid on;
xlabel('Angle (degrees)', 'FontSize', 11);
ylabel('Normalized Gain (dB)', 'FontSize', 11);
title('1D Beam Pattern (Azimuth Cut)', 'FontSize', 12);
xlim([-90, 90]);
ylim([-40, 5]);
legend('Pattern', 'Steering angle', '-3 dB', 'Location', 'best');

%% Plot 2: 1D Beam Pattern (Polar)
subplot(2,3,2);
pattern_1d_linear = 10.^(pattern_1d_dB / 20);
pattern_1d_linear = pattern_1d_linear / max(pattern_1d_linear);
polarplot(deg2rad(angles_1d), pattern_1d_linear, 'b-', 'LineWidth', 2);
hold on;
polarplot(deg2rad([beam_angle_deg beam_angle_deg]), [0 1], 'r--', 'LineWidth', 2);
hold off;
ax = gca;
ax.ThetaZeroLocation = 'right';
ax.ThetaDir = 'counterclockwise';
ax.RLim = [0 1.1];
rticks([0.1 0.25 0.5 0.71 1.0]);
rticklabels({'-20dB', '-12dB', '-6dB', '-3dB', '0dB'});
title('Polar Pattern', 'FontSize', 12);

%% Plot 3: Phase Distribution
subplot(2,3,3);
phases_deg = mod(rad2deg(phases), 360);
phase_grid = reshape(phases_deg, N, N);
x_grid = reshape(x_elem, N, N);
y_grid = reshape(y_elem, N, N);
imagesc(x_grid(1,:)*1000, y_grid(:,1)*1000, phase_grid);
colormap(gca, hsv(256));
cb = colorbar;
cb.Label.String = 'Phase (°)';
caxis([0 360]);
axis equal tight;
xlabel('X (mm)', 'FontSize', 11);
ylabel('Y (mm)', 'FontSize', 11);
title('Phase Distribution', 'FontSize', 12);
set(gca, 'YDir', 'normal');

%% Plot 4: 3D Radiation Pattern (Cartesian)
subplot(2,3,4);
surf(THETA, PHI, AF_dB, 'EdgeColor', 'none');
colormap(gca, jet(256));
colorbar;
caxis([-30 0]);
xlabel('Elevation θ (°)', 'FontSize', 11);
ylabel('Azimuth φ (°)', 'FontSize', 11);
zlabel('Gain (dB)', 'FontSize', 11);
title('3D Far-Field Pattern', 'FontSize', 12);
view(45, 30);

%% Plot 5: 2D Heatmap
subplot(2,3,5);
imagesc(theta, phi, AF_dB);
colormap(gca, jet(256));
colorbar;
caxis([-30 0]);
xlabel('Elevation θ (°)', 'FontSize', 11);
ylabel('Azimuth φ (°)', 'FontSize', 11);
title('2D Heatmap (Top View)', 'FontSize', 12);
axis xy;

%% Plot 6: Peak Direction and Statistics
subplot(2,3,6);
axis off;
stats_text = sprintf([...
    'RIS Beam Pattern Summary\n' ...
    '========================\n\n' ...
    'Array Configuration:\n' ...
    '  Size: %dx%d elements\n' ...
    '  Frequency: %.2f GHz\n' ...
    '  Wavelength: %.4f m\n' ...
    '  Element spacing: %.4f m\n\n' ...
    'Steering Parameters:\n' ...
    '  Steering angle: %.1f°\n' ...
    '  Quantization: %d-bit\n\n' ...
    'Beam Metrics:\n' ...
    '  Peak direction: θ=%.1f°, φ=%.1f°\n' ...
    '  Main lobe width: %.1f°\n' ...
    '  Sidelobe level: %.1f dB\n' ...
    '  Array gain: %.1f dBi\n\n' ...
    'Array Gain Formula:\n' ...
    '  G = 10*log10(N²) ≈ %.1f dBi' ...
    ], N, N, freq/1e9, lambda, spacing, ...
    beam_angle_deg, bits, peak_theta, peak_phi, main_lobe_width, sidelobe_level, ...
    10*log10(N*N) + 5, 10*log10(N*N) + 5);

text(0.1, 0.5, stats_text, 'FontSize', 10, ...
     'VerticalAlignment', 'middle', 'HorizontalAlignment', 'left');

sgtitle(sprintf('RIS %dx%d Far-Field @ %.2f GHz | Beam Steering: %.1f°', ...
                N, N, freq/1e9, beam_angle_deg), 'FontSize', 14, 'FontWeight', 'bold');

fprintf('Done! Figure displayed.\n\n');

%% Save Results
save_fig = true;
if save_fig
    filename = sprintf('ris_beam_%dbit_%ddeg.png', bits, round(beam_angle_deg));
    saveas(fig, filename);
    fprintf('Figure saved as: %s\n', filename);
end
