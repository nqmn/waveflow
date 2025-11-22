function result = sweep_beam_snr(elem_pos, freq, N, bits, ap_pos, ris_pos, ue_pos, tx_power_dBm, angle_range, angle_step)
    % Sweep beam angles and compute directivity/SNR for each to find optimal
    %
    % Two modes:
    %   1. UE-aware mode: If ue_pos is provided, compute SNR at UE direction
    %   2. Discovery mode: If ue_pos is empty, sweep to find peak directivity
    %
    % Inputs:
    %   elem_pos     - Element positions (N*N x 3) in meters
    %   freq         - Frequency in Hz
    %   N            - Array size (NxN)
    %   bits         - Phase quantization bits (0 = continuous)
    %   ap_pos       - AP position [x, y, z] in meters
    %   ris_pos      - RIS center position [x, y, z] in meters
    %   ue_pos       - UE position [x, y, z] in meters (empty for discovery mode)
    %   tx_power_dBm - Transmit power in dBm
    %   angle_range  - [min_angle, max_angle] in degrees
    %   angle_step   - Angle step in degrees
    %
    % Outputs:
    %   result - Struct with optimal angle, directivity/SNR values, and plot data

    c = 3e8;
    lambda = c / freq;
    k = 2 * pi / lambda;

    % Default parameters
    if nargin < 10 || isempty(angle_step)
        angle_step = 1;
    end
    if nargin < 9 || isempty(angle_range)
        angle_range = [-90, 90];
    end
    if nargin < 8 || isempty(tx_power_dBm)
        tx_power_dBm = 20;
    end

    % Determine mode
    discovery_mode = isempty(ue_pos);

    % Compute geometry
    ap_pos = ap_pos(:)';
    ris_pos = ris_pos(:)';

    % Distances
    d_ap_ris = norm(ris_pos - ap_pos);

    % Compute incident angle from RIS perspective (AP direction)
    vec_ap = ap_pos - ris_pos;
    incident_angle = atan2d(vec_ap(2), vec_ap(1));

    % Element positions centered
    x_pos = elem_pos(:,1) - mean(elem_pos(:,1));
    y_pos = elem_pos(:,2) - mean(elem_pos(:,2));

    % Sweep angles
    angles = angle_range(1):angle_step:angle_range(2);
    n_angles = length(angles);

    N_elem = size(elem_pos, 1);

    if discovery_mode
        % Discovery mode: compute peak directivity for each steering angle
        directivity_values = zeros(1, n_angles);

        % Fine angular grid for computing directivity
        eval_angles = -90:0.5:90;

        for idx = 1:n_angles
            beam_angle = angles(idx);

            % Compute steering phases for this beam angle
            phases = -k * (x_pos * cosd(beam_angle) + y_pos * sind(beam_angle));

            % Apply quantization
            if bits > 0
                num_levels = 2^bits;
                phase_step = 2*pi / num_levels;
                phases = round(phases / phase_step) * phase_step;
            end

            % Compute array factor over all evaluation angles
            AF_pattern = zeros(1, length(eval_angles));
            for a_idx = 1:length(eval_angles)
                eval_ang = eval_angles(a_idx);
                kx = k * cosd(eval_ang);
                ky = k * sind(eval_ang);

                AF = 0;
                for n = 1:N_elem
                    phase_shift = kx * elem_pos(n,1) + ky * elem_pos(n,2);
                    AF = AF + exp(1j * (phases(n) + phase_shift));
                end
                AF_pattern(a_idx) = abs(AF);
            end

            % Peak directivity (normalized)
            AF_max = max(AF_pattern);
            directivity_values(idx) = 20 * log10(AF_max / N_elem + 1e-10);
        end

        % Find optimal angle (peak directivity)
        [max_directivity, max_idx] = max(directivity_values);
        optimal_angle = angles(max_idx);

        % Create figure
        figure('Name', 'Beam Angle Discovery Sweep', 'NumberTitle', 'off', ...
               'Position', [100 100 1200 700], 'Color', 'w');

        % === Directivity vs Angle ===
        subplot(2,2,[1,2]);
        plot(angles, directivity_values, 'b-', 'LineWidth', 2);
        hold on;
        plot(optimal_angle, max_directivity, 'ro', 'MarkerSize', 12, 'MarkerFaceColor', 'r');
        xline(optimal_angle, 'r--', 'LineWidth', 1.5);
        hold off;
        grid on;
        xlabel('Beam Steering Angle (degrees)', 'FontSize', 11);
        ylabel('Peak Directivity (dB)', 'FontSize', 11);
        title(sprintf('Directivity vs Beam Angle (%d-bit, %dx%d array) - Discovery Mode', bits, N, N), 'FontSize', 13);
        legend('Directivity', sprintf('Optimal: %.1f deg (%.1f dB)', optimal_angle, max_directivity), ...
               'Location', 'best');
        xlim(angle_range);

        % === Geometry Plot ===
        subplot(2,2,3);
        hold on;

        % Plot AP, RIS
        plot(ap_pos(1), ap_pos(2), 'bs', 'MarkerSize', 15, 'MarkerFaceColor', 'b', 'LineWidth', 2);
        plot(ris_pos(1), ris_pos(2), 'r^', 'MarkerSize', 15, 'MarkerFaceColor', 'r', 'LineWidth', 2);

        % Draw AP to RIS path
        plot([ap_pos(1), ris_pos(1)], [ap_pos(2), ris_pos(2)], 'b--', 'LineWidth', 1.5);

        % Draw optimal beam direction
        beam_len = d_ap_ris * 0.6;
        % Optimal beam direction is relative to the incident angle
        abs_optimal = incident_angle + optimal_angle;
        beam_x = ris_pos(1) + beam_len * cosd(abs_optimal);
        beam_y = ris_pos(2) + beam_len * sind(abs_optimal);
        quiver(ris_pos(1), ris_pos(2), beam_x - ris_pos(1), beam_y - ris_pos(2), 0, ...
               'r', 'LineWidth', 2.5, 'MaxHeadSize', 0.5);

        % Draw RIS normal (assuming +x direction)
        normal_len = d_ap_ris * 0.3;
        quiver(ris_pos(1), ris_pos(2), normal_len, 0, 0, ...
               'k--', 'LineWidth', 1, 'MaxHeadSize', 0.3);

        hold off;
        axis equal;
        grid on;
        xlabel('X (m)');
        ylabel('Y (m)');
        title('Network Geometry (Discovery Mode)');
        legend('AP', 'RIS', 'AP to RIS', sprintf('Optimal Beam (%.1f deg)', optimal_angle), 'RIS Normal', ...
               'Location', 'best');

        % === Phase Heatmap at Optimal ===
        subplot(2,2,4);
        optimal_phases = -k * (x_pos * cosd(optimal_angle) + y_pos * sind(optimal_angle));
        if bits > 0
            num_levels = 2^bits;
            phase_step = 2*pi / num_levels;
            optimal_phases = round(optimal_phases / phase_step) * phase_step;
        end
        phases_deg = mod(rad2deg(optimal_phases), 360);
        phase_grid = reshape(phases_deg, N, N);
        imagesc(phase_grid);
        colormap(gca, hsv(256));
        colorbar;
        caxis([0 360]);
        axis equal tight;
        title(sprintf('Phase @ Optimal (%.1f deg)', optimal_angle));
        xlabel('Element X');
        ylabel('Element Y');

        % Overall title
        sgtitle(sprintf('Beam Discovery Sweep: AP(%.1f,%.1f) to RIS(%.1f,%.1f)\nIncident: %.1f deg, Optimal Steering: %.1f deg', ...
                ap_pos(1), ap_pos(2), ris_pos(1), ris_pos(2), ...
                incident_angle, optimal_angle), ...
                'FontSize', 12, 'FontWeight', 'bold');

        % Return results for discovery mode
        result.angles = angles;
        result.snr_values = directivity_values;  % Use snr_values field for compatibility
        result.optimal_angle = optimal_angle;
        result.optimal_snr = max_directivity;  % Use snr field for compatibility
        result.deflection_angle = optimal_angle;  % Same as optimal in discovery
        result.snr_at_deflection = max_directivity;
        result.incident_angle = incident_angle;
        result.target_angle = incident_angle + optimal_angle;  % Absolute direction
        result.d_ap_ris = d_ap_ris;
        result.d_ris_ue = 0;  % Unknown in discovery mode
        result.discovery_mode = true;

    else
        % UE-aware mode: original behavior - compute SNR at known UE
        ue_pos = ue_pos(:)';
        d_ris_ue = norm(ue_pos - ris_pos);

        vec_ue = ue_pos - ris_pos;
        target_angle = atan2d(vec_ue(2), vec_ue(1));      % UE direction from RIS

        % Deflection angle (theta_out - theta_in)
        deflection = target_angle - incident_angle;
        while deflection > 180
            deflection = deflection - 360;
        end
        while deflection < -180
            deflection = deflection + 360;
        end

        % Path loss calculation (free space)
        PL_ap_ris = 20*log10(4*pi*d_ap_ris/lambda);
        PL_ris_ue = 20*log10(4*pi*d_ris_ue/lambda);

        % Noise floor (100 MHz BW, 6 dB NF)
        bandwidth_MHz = 100;
        noise_figure_dB = 6;
        noise_floor_dBm = -174 + 10*log10(bandwidth_MHz * 1e6) + noise_figure_dB;

        snr_values = zeros(1, n_angles);
        gain_values = zeros(1, n_angles);
        af_at_ue = zeros(1, n_angles);

        for idx = 1:n_angles
            beam_angle = angles(idx);

            % Compute steering phases
            phases = -k * (x_pos * cosd(beam_angle) + y_pos * sind(beam_angle));

            % Apply quantization
            if bits > 0
                num_levels = 2^bits;
                phase_step = 2*pi / num_levels;
                phases = round(phases / phase_step) * phase_step;
            end

            % Compute array factor at UE direction
            kx_ue = k * cosd(target_angle);
            ky_ue = k * sind(target_angle);

            AF = 0;
            for n = 1:N_elem
                phase_shift = kx_ue * elem_pos(n,1) + ky_ue * elem_pos(n,2);
                AF = AF + exp(1j * (phases(n) + phase_shift));
            end

            AF_mag = abs(AF);
            AF_max = N_elem;  % Maximum possible (all in phase)
            AF_norm = AF_mag / AF_max;
            AF_dB = 20 * log10(AF_norm + 1e-10);

            af_at_ue(idx) = AF_dB;

            % Array gain (ideal + AF penalty)
            ideal_gain_dBi = 10*log10(N_elem) + 5;  % ~5 dBi element gain
            actual_gain_dBi = ideal_gain_dBi + AF_dB;

            % Quantization loss
            if bits > 0
                x = 1 / (2^bits);
                if x == 0
                    sinc_val = 1;
                else
                    sinc_val = sin(pi * x) / (pi * x);
                end
                quant_loss_dB = -10*log10(sinc_val^2);
            else
                quant_loss_dB = 0;
            end

            gain_values(idx) = actual_gain_dBi - quant_loss_dB;

            % SNR calculation
            Gt = 3;  % AP antenna gain
            Gr = 3;  % UE antenna gain
            Pr_dBm = tx_power_dBm + Gt + Gr + gain_values(idx) - PL_ap_ris - PL_ris_ue;
            snr_values(idx) = Pr_dBm - noise_floor_dBm;
        end

        % Find optimal
        [max_snr, max_idx] = max(snr_values);
        optimal_angle = angles(max_idx);

        % Find SNR at theoretical deflection angle
        [~, deflection_idx] = min(abs(angles - deflection));
        snr_at_deflection = snr_values(deflection_idx);

        % Create figure
        figure('Name', 'Beam Angle vs SNR Sweep', 'NumberTitle', 'off', ...
               'Position', [100 100 1400 800], 'Color', 'w');

        % === SNR vs Angle ===
        subplot(2,3,[1,2]);
        plot(angles, snr_values, 'b-', 'LineWidth', 2);
        hold on;
        plot(optimal_angle, max_snr, 'ro', 'MarkerSize', 12, 'MarkerFaceColor', 'r');
        plot(deflection, snr_at_deflection, 'g^', 'MarkerSize', 12, 'MarkerFaceColor', 'g');
        xline(deflection, 'g--', 'LineWidth', 1.5);
        xline(optimal_angle, 'r--', 'LineWidth', 1.5);
        hold off;
        grid on;
        xlabel('Beam Steering Angle (degrees)', 'FontSize', 11);
        ylabel('SNR (dB)', 'FontSize', 11);
        title(sprintf('SNR vs Beam Angle (%d-bit, %dx%d array)', bits, N, N), 'FontSize', 13);
        legend('SNR', sprintf('Optimal: %.1f deg (%.1f dB)', optimal_angle, max_snr), ...
               sprintf('Deflection: %.1f deg (%.1f dB)', deflection, snr_at_deflection), ...
               'Location', 'best');
        xlim(angle_range);

        % === Array Factor at UE ===
        subplot(2,3,3);
        plot(angles, af_at_ue, 'b-', 'LineWidth', 1.5);
        hold on;
        plot(optimal_angle, af_at_ue(max_idx), 'ro', 'MarkerSize', 10, 'MarkerFaceColor', 'r');
        plot(deflection, af_at_ue(deflection_idx), 'g^', 'MarkerSize', 10, 'MarkerFaceColor', 'g');
        hold off;
        grid on;
        xlabel('Beam Angle (deg)');
        ylabel('Array Factor at UE (dB)');
        title('Array Factor Response at UE');
        xlim(angle_range);

        % === Geometry Plot ===
        subplot(2,3,4);
        hold on;

        plot(ap_pos(1), ap_pos(2), 'bs', 'MarkerSize', 15, 'MarkerFaceColor', 'b', 'LineWidth', 2);
        plot(ris_pos(1), ris_pos(2), 'r^', 'MarkerSize', 15, 'MarkerFaceColor', 'r', 'LineWidth', 2);
        plot(ue_pos(1), ue_pos(2), 'go', 'MarkerSize', 15, 'MarkerFaceColor', 'g', 'LineWidth', 2);

        plot([ap_pos(1), ris_pos(1)], [ap_pos(2), ris_pos(2)], 'b--', 'LineWidth', 1.5);
        plot([ris_pos(1), ue_pos(1)], [ris_pos(2), ue_pos(2)], 'g--', 'LineWidth', 1.5);

        beam_len = max(d_ap_ris, d_ris_ue) * 0.5;
        beam_x = ris_pos(1) + beam_len * cosd(target_angle);
        beam_y = ris_pos(2) + beam_len * sind(target_angle);
        quiver(ris_pos(1), ris_pos(2), beam_x - ris_pos(1), beam_y - ris_pos(2), 0, ...
               'r', 'LineWidth', 2, 'MaxHeadSize', 0.5);

        hold off;
        axis equal;
        grid on;
        xlabel('X (m)');
        ylabel('Y (m)');
        title('Network Geometry');
        legend('AP', 'RIS', 'UE', 'AP to RIS', 'RIS to UE', 'Beam to UE', 'Location', 'best');

        % === Phase Heatmap at Optimal ===
        subplot(2,3,5);
        optimal_phases = -k * (x_pos * cosd(optimal_angle) + y_pos * sind(optimal_angle));
        if bits > 0
            num_levels = 2^bits;
            phase_step = 2*pi / num_levels;
            optimal_phases = round(optimal_phases / phase_step) * phase_step;
        end
        phases_deg = mod(rad2deg(optimal_phases), 360);
        phase_grid = reshape(phases_deg, N, N);
        imagesc(phase_grid);
        colormap(gca, hsv(256));
        colorbar;
        caxis([0 360]);
        axis equal tight;
        title(sprintf('Phase @ Optimal (%.1f deg)', optimal_angle));
        xlabel('Element X');
        ylabel('Element Y');

        % === Phase Heatmap at Deflection ===
        subplot(2,3,6);
        deflection_phases = -k * (x_pos * cosd(deflection) + y_pos * sind(deflection));
        if bits > 0
            deflection_phases = round(deflection_phases / phase_step) * phase_step;
        end
        phases_deg_def = mod(rad2deg(deflection_phases), 360);
        phase_grid_def = reshape(phases_deg_def, N, N);
        imagesc(phase_grid_def);
        colormap(gca, hsv(256));
        colorbar;
        caxis([0 360]);
        axis equal tight;
        title(sprintf('Phase @ Deflection (%.1f deg)', deflection));
        xlabel('Element X');
        ylabel('Element Y');

        % Overall title
        sgtitle(sprintf('Beam Sweep Analysis: AP(%.1f,%.1f) to RIS(%.1f,%.1f) to UE(%.1f,%.1f)\nIncident: %.1f deg, Target: %.1f deg, Deflection: %.1f deg', ...
                ap_pos(1), ap_pos(2), ris_pos(1), ris_pos(2), ue_pos(1), ue_pos(2), ...
                incident_angle, target_angle, deflection), ...
                'FontSize', 12, 'FontWeight', 'bold');

        % Return results
        result.angles = angles;
        result.snr_values = snr_values;
        result.optimal_angle = optimal_angle;
        result.optimal_snr = max_snr;
        result.deflection_angle = deflection;
        result.snr_at_deflection = snr_at_deflection;
        result.incident_angle = incident_angle;
        result.target_angle = target_angle;
        result.d_ap_ris = d_ap_ris;
        result.d_ris_ue = d_ris_ue;
        result.discovery_mode = false;
    end
end
