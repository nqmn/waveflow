function [angles, pattern_dB, metrics] = compute_beam_pattern(N, freq, beam_angle, spacing, bits, do_plot)
    % Compute beam pattern for uniform planar array with phase steering
    %
    % Inputs:
    %   N          - Array size (NxN elements)
    %   freq       - Frequency in Hz
    %   beam_angle - Steering angle in degrees (azimuth)
    %   spacing    - Element spacing in meters
    %   bits       - Quantization bits (0 = continuous phases)
    %   do_plot    - Boolean to plot result
    %
    % Outputs:
    %   angles     - Angle vector (degrees)
    %   pattern_dB - Normalized pattern in dB
    %   metrics    - Struct with main_lobe_width, sidelobe_level

    c = 3e8;
    lambda = c / freq;
    k = 2 * pi / lambda;

    % Generate element positions (centered planar array in XY plane)
    [row, col] = meshgrid(0:N-1, 0:N-1);
    x_pos = (row(:) - (N-1)/2) * spacing;
    y_pos = (col(:) - (N-1)/2) * spacing;

    % Compute steering phases for desired beam angle
    % Phase gradient to steer beam to beam_angle (azimuth)
    phases = -k * (x_pos * cosd(beam_angle) + y_pos * sind(beam_angle));

    % Apply quantization if specified
    if bits > 0
        num_levels = 2^bits;
        phase_step = 2*pi / num_levels;
        phases = round(phases / phase_step) * phase_step;
    end

    % Compute 1D pattern (azimuth cut at elevation = 0)
    angles = -90:0.5:90;
    pattern = zeros(size(angles));

    for idx = 1:length(angles)
        ang = angles(idx);
        % Wave vector for this direction (elevation = 0)
        kx = k * cosd(ang);
        ky = k * sind(ang);
        % Array factor
        steering = kx * x_pos + ky * y_pos;
        pattern(idx) = abs(sum(exp(1j * (phases + steering))));
    end

    % Normalize to dB
    pattern_max = max(pattern);
    if pattern_max > 0
        pattern_dB = 20 * log10(pattern / pattern_max);
    else
        pattern_dB = zeros(size(pattern));
    end
    pattern_dB(pattern_dB < -40) = -40;

    % Compute metrics
    [~, peak_idx] = max(pattern_dB);

    % Main lobe width (-3 dB beamwidth)
    above_3dB = pattern_dB >= -3;
    main_lobe_indices = find(above_3dB);
    if ~isempty(main_lobe_indices)
        main_lobe_width = (main_lobe_indices(end) - main_lobe_indices(1)) * 0.5;
    else
        main_lobe_width = 0;
    end

    % Sidelobe level - find max outside main lobe (-3dB region)
    main_lobe_end = peak_idx;
    for ii = peak_idx:length(pattern_dB)-1
        if pattern_dB(ii) >= -3 && pattern_dB(ii+1) < -3
            main_lobe_end = ii + 1;
            break;
        end
    end
    
    if main_lobe_end < length(pattern_dB) - 3
        sidelobe_region = pattern_dB(main_lobe_end+2:end);
        sidelobe_level = max(sidelobe_region);
    else
        main_lobe_start = peak_idx;
        for ii = peak_idx:-1:2
            if pattern_dB(ii) >= -3 && pattern_dB(ii-1) < -3
                main_lobe_start = ii - 1;
                break;
            end
        end
        if main_lobe_start > 3
            sidelobe_level = max(pattern_dB(1:main_lobe_start-2));
        else
            sidelobe_level = -30;
        end
    end

    metrics.main_lobe_width = main_lobe_width;
    metrics.sidelobe_level = sidelobe_level;

    % Plot if requested
    if do_plot
        figure('Name', 'Beam Pattern', 'NumberTitle', 'off');

        % Cartesian plot
        subplot(1,2,1);
        plot(angles, pattern_dB, 'b-', 'LineWidth', 1.5);
        hold on;
        xline(beam_angle, 'r--', 'LineWidth', 1.5);
        yline(-3, 'g--', 'LineWidth', 1);
        hold off;
        grid on;
        xlabel('Angle (degrees)');
        ylabel('Normalized Pattern (dB)');

        if bits > 0
            title_str = sprintf('Beam Pattern (N=%d, \\theta=%.1f°, %d-bit)', N, beam_angle, bits);
        else
            title_str = sprintf('Beam Pattern (N=%d, \\theta=%.1f°, continuous)', N, beam_angle);
        end
        title(title_str);
        xlim([-90, 90]);
        ylim([-40, 5]);
        legend('Pattern', 'Target Angle', '-3 dB', 'Location', 'best');

        % Polar plot
        subplot(1,2,2);
        % Shift pattern for polar plot (add 40 dB offset for visibility)
        polar_pattern = pattern_dB + 40;
        polar_pattern(polar_pattern < 0) = 0;
        polarplot(deg2rad(angles), polar_pattern, 'b-', 'LineWidth', 1.5);
        hold on;
        polarplot(deg2rad([beam_angle beam_angle]), [0 40], 'r--', 'LineWidth', 1.5);
        hold off;
        rlim([0 45]);
        title('Polar Pattern');

        % Add metrics annotation
        annotation('textbox', [0.35, 0.02, 0.3, 0.08], ...
            'String', sprintf('Beamwidth: %.1f°  |  SLL: %.1f dB', main_lobe_width, sidelobe_level), ...
            'HorizontalAlignment', 'center', ...
            'EdgeColor', 'none', 'FontSize', 10);
    end
end
