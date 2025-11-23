%% Compare Multiple Beam Steering Angles
% Run multiple steering angles to see how the beam pattern changes

clear all; close all; clc;

%% Configuration
N = 16;                  % Array size
freq = 5.8e9;           % Frequency
c = 3e8;
lambda = c / freq;
k = 2 * pi / lambda;
spacing = lambda / 2;

% Steering angles to compare (in degrees)
steering_angles = [0, 15, 30, 45, 60, 90];
bits = 3;  % 3-bit quantization

fprintf('\n========================================\n');
fprintf('Comparing Beam Patterns at Different Angles\n');
fprintf('========================================\n\n');

% Create figure with subplots
fig = figure('Name', 'Beam Pattern Comparison', 'NumberTitle', 'off', ...
             'Position', [100 100 1600 1000]);

num_angles = length(steering_angles);

for angle_idx = 1:num_angles
    beam_angle_deg = steering_angles(angle_idx);

    %% Generate Element Positions
    [row, col] = meshgrid(0:N-1, 0:N-1);
    x_elem = (row(:) - (N-1)/2) * spacing;
    y_elem = (col(:) - (N-1)/2) * spacing;
    z_elem = zeros(size(x_elem));

    %% Compute Phases
    phases = -k * (x_elem * cosd(beam_angle_deg) + y_elem * sind(beam_angle_deg));

    % Quantize
    if bits > 0
        num_levels = 2^bits;
        phase_step = 2*pi / num_levels;
        phases = round(phases / phase_step) * phase_step;
    end

    %% Compute 1D Pattern
    angles_1d = -90:0.5:90;
    pattern_1d = zeros(size(angles_1d));

    for idx = 1:length(angles_1d)
        ang = angles_1d(idx);
        kx = k * cosd(ang);
        ky = k * sind(ang);
        steering = kx * x_elem + ky * y_elem;
        pattern_1d(idx) = abs(sum(exp(1j * (phases + steering))));
    end

    % Normalize
    pattern_1d_max = max(pattern_1d);
    pattern_1d_dB = 20 * log10(pattern_1d / pattern_1d_max + 1e-10);
    pattern_1d_dB = max(pattern_1d_dB, -40);

    % Plot
    subplot(2, 3, angle_idx);
    plot(angles_1d, pattern_1d_dB, 'LineWidth', 2);
    hold on;
    plot(beam_angle_deg, max(pattern_1d_dB)-3, 'ro', 'MarkerSize', 10, 'MarkerFaceColor', 'r');
    yline(-3, 'g--', 'LineWidth', 1);
    hold off;
    grid on;
    xlabel('Angle (°)', 'FontSize', 10);
    ylabel('Gain (dB)', 'FontSize', 10);
    title(sprintf('Steering Angle: %.0f°', beam_angle_deg), 'FontSize', 11);
    xlim([-90, 90]);
    ylim([-40, 5]);

    fprintf('Angle: %3.0f° | Peak at: %6.1f° | Peak gain: %6.1f dB\n', ...
            beam_angle_deg, angles_1d(find(pattern_1d_dB == max(pattern_1d_dB), 1)), ...
            max(pattern_1d_dB));
end

sgtitle(sprintf('RIS Beam Pattern - %d-bit Quantization', bits), ...
        'FontSize', 14, 'FontWeight', 'bold');

fprintf('\n========================================\n');
fprintf('Comparison complete!\n');
fprintf('========================================\n\n');
