function result = sweep_beam_snr(elem_pos, freq, N, bits, ap_pos, ris_pos, ue_pos, tx_power_dBm, angle_range, angle_step, ris_normal_deg, max_steering_deg)
    % Sweep beam angles and compute directivity/SNR for each to find optimal
    %
    % Two modes:
    %   1. UE-aware mode: If ue_pos is provided, compute SNR at UE direction
    %   2. Discovery mode: If ue_pos is empty, sweep to find peak directivity
    %
    % Inputs:
    %   elem_pos        - Element positions (N*N x 3) in meters
    %   freq            - Frequency in Hz
    %   N               - Array size (NxN)
    %   bits            - Phase quantization bits (0 = continuous)
    %   ap_pos          - AP position [x, y, z] in meters
    %   ris_pos         - RIS center position [x, y, z] in meters
    %   ue_pos          - UE position [x, y, z] in meters (empty for discovery mode)
    %   tx_power_dBm    - Transmit power in dBm
    %   angle_range     - [min_angle, max_angle] in degrees (relative to RIS normal)
    %   angle_step      - Angle step in degrees
    %   ris_normal_deg  - RIS normal angle in degrees (0 = +x direction)
    %   max_steering_deg - Maximum steering angle from normal (for FoV)
    %
    % Outputs:
    %   result - Struct with optimal angle, directivity/SNR values, and plot data

    c = 3e8;
    lambda = c / freq;
    k = 2 * pi / lambda;

    % Default parameters
    if nargin < 12 || isempty(max_steering_deg)
        max_steering_deg = 60;
    end
    if nargin < 11 || isempty(ris_normal_deg)
        ris_normal_deg = 0;
    end
    if nargin < 10 || isempty(angle_step)
        angle_step = 1;
    end
    if nargin < 9 || isempty(angle_range)
        angle_range = [-max_steering_deg, max_steering_deg];
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

    % Compute incident angle from RIS perspective (AP direction, absolute)
    vec_ap = ap_pos - ris_pos;
    incident_angle_abs = atan2d(vec_ap(2), vec_ap(1));

    % Incident angle relative to RIS normal
    incident_angle_rel = incident_angle_abs - ris_normal_deg;
    % Normalize to [-180, 180]
    while incident_angle_rel > 180
        incident_angle_rel = incident_angle_rel - 360;
    end
    while incident_angle_rel < -180
        incident_angle_rel = incident_angle_rel + 360;
    end

    % Element positions centered
    x_pos = elem_pos(:,1) - mean(elem_pos(:,1));
    y_pos = elem_pos(:,2) - mean(elem_pos(:,2));

    % Sweep angles in ABSOLUTE coordinates (global reference frame, same as connect command)
    % This matches the deflection_angle_deg = theta_out_rad - theta_in_rad in connection_handler.py
    angles_abs = angle_range(1):angle_step:angle_range(2);

    % Convert to absolute angles by adding to incident angle
    % angles_abs represents the deflection from incident direction
    % So absolute beam angle = incident_angle_abs + angles_abs
    angles = angles_abs;  % We'll use these as deflection angles and convert as needed
    n_angles = length(angles);

    N_elem = size(elem_pos, 1);

    if discovery_mode
        % Discovery mode: compute peak directivity for each steering angle
        % Sweep angles are RELATIVE to RIS normal
        directivity_values = zeros(1, n_angles);

        % Fine angular grid for computing directivity (relative to RIS normal)
        eval_angles_rel = -90:0.5:90;

        for idx = 1:n_angles
            % beam_angle is relative to RIS normal
            beam_angle_rel = angles(idx);
            % Convert to absolute for phase computation
            beam_angle_abs = ris_normal_deg + beam_angle_rel;

            % Compute steering phases for this beam angle (absolute)
            phases = -k * (x_pos * cosd(beam_angle_abs) + y_pos * sind(beam_angle_abs));

            % Apply quantization
            if bits > 0
                num_levels = 2^bits;
                phase_step = 2*pi / num_levels;
                phases = round(phases / phase_step) * phase_step;
            end

            % Compute array factor over all evaluation angles
            AF_pattern = zeros(1, length(eval_angles_rel));
            for a_idx = 1:length(eval_angles_rel)
                % Convert eval angle to absolute
                eval_ang_abs = ris_normal_deg + eval_angles_rel(a_idx);
                kx = k * cosd(eval_ang_abs);
                ky = k * sind(eval_ang_abs);

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

        % Find optimal angle (peak directivity) - this is RELATIVE to RIS normal
        [max_directivity, max_idx] = max(directivity_values);
        optimal_angle_rel = angles(max_idx);
        optimal_angle_abs = ris_normal_deg + optimal_angle_rel;

        % Create figure
        figure('Name', 'Beam Angle Discovery Sweep', 'NumberTitle', 'off', ...
               'Position', [100 100 1200 700], 'Color', 'w');

        % === Directivity vs Angle ===
        subplot(2,2,[1,2]);
        plot(angles, directivity_values, 'b-', 'LineWidth', 2);
        hold on;
        plot(optimal_angle_rel, max_directivity, 'ro', 'MarkerSize', 12, 'MarkerFaceColor', 'r');
        xline(optimal_angle_rel, 'r--', 'LineWidth', 1.5);
        % Mark incident angle relative to normal
        xline(incident_angle_rel, 'g:', 'LineWidth', 1.5);
        hold off;
        grid on;
        xlabel('Beam Steering Angle (degrees from RIS normal)', 'FontSize', 11);
        ylabel('Peak Directivity (dB)', 'FontSize', 11);
        title(sprintf('Directivity vs Beam Angle (%d-bit, %dx%d array) - Discovery Mode', bits, N, N), 'FontSize', 13);
        legend('Directivity', sprintf('Optimal: %.1f deg (%.1f dB)', optimal_angle_rel, max_directivity), ...
               sprintf('Incident: %.1f deg', incident_angle_rel), 'Location', 'best');
        xlim(angle_range);

        % === Geometry Plot ===
        subplot(2,2,3);
        hold on;

        % Plot AP, RIS
        plot(ap_pos(1), ap_pos(2), 'gs', 'MarkerSize', 15, 'MarkerFaceColor', 'g', 'LineWidth', 2);
        plot(ris_pos(1), ris_pos(2), 'r^', 'MarkerSize', 15, 'MarkerFaceColor', 'r', 'LineWidth', 2);

        % Draw AP to RIS path
        plot([ap_pos(1), ris_pos(1)], [ap_pos(2), ris_pos(2)], 'g--', 'LineWidth', 1.5);

        % Draw optimal beam direction (absolute)
        beam_len = d_ap_ris * 0.6;
        beam_x = ris_pos(1) + beam_len * cosd(optimal_angle_abs);
        beam_y = ris_pos(2) + beam_len * sind(optimal_angle_abs);
        quiver(ris_pos(1), ris_pos(2), beam_x - ris_pos(1), beam_y - ris_pos(2), 0, ...
               'Color', [1 0.3 0], 'LineWidth', 2.5, 'MaxHeadSize', 0.5);

        % Draw RIS normal direction (absolute)
        normal_len = d_ap_ris * 0.3;
        normal_x = ris_pos(1) + normal_len * cosd(ris_normal_deg);
        normal_y = ris_pos(2) + normal_len * sind(ris_normal_deg);
        quiver(ris_pos(1), ris_pos(2), normal_x - ris_pos(1), normal_y - ris_pos(2), 0, ...
               'k', 'LineWidth', 1.5, 'MaxHeadSize', 0.3);

        % Draw FoV arc
        arc_radius = d_ap_ris * 0.4;
        arc_angles = linspace(ris_normal_deg - max_steering_deg, ris_normal_deg + max_steering_deg, 50);
        arc_x = ris_pos(1) + arc_radius * cosd(arc_angles);
        arc_y = ris_pos(2) + arc_radius * sind(arc_angles);
        plot(arc_x, arc_y, 'y-', 'LineWidth', 2);

        hold off;
        axis equal;
        grid on;
        xlabel('X (m)');
        ylabel('Y (m)');
        title('Network Geometry (Discovery Mode)');
        legend('AP', 'RIS', 'AP to RIS', sprintf('Beam (%.1f deg abs)', optimal_angle_abs), ...
               sprintf('Normal (%.1f deg)', ris_normal_deg), sprintf('FoV (+/-%.0f deg)', max_steering_deg), ...
               'Location', 'best');

        % === Phase Heatmap at Optimal ===
        subplot(2,2,4);
        optimal_phases = -k * (x_pos * cosd(optimal_angle_abs) + y_pos * sind(optimal_angle_abs));
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
        title(sprintf('Phase @ Optimal (%.1f deg from normal)', optimal_angle_rel));
        xlabel('Element X');
        ylabel('Element Y');

        % Overall title
        sgtitle(sprintf('Beam Discovery Sweep: AP(%.1f,%.1f) to RIS(%.1f,%.1f)\nRIS Normal: %.1f deg, Incident: %.1f deg (rel), Optimal: %.1f deg (rel) = %.1f deg (abs)', ...
                ap_pos(1), ap_pos(2), ris_pos(1), ris_pos(2), ...
                ris_normal_deg, incident_angle_rel, optimal_angle_rel, optimal_angle_abs), ...
                'FontSize', 11, 'FontWeight', 'bold');

        % Return results for discovery mode
        % Angles are relative to RIS normal for consistency
        result.angles = angles;
        result.snr_values = directivity_values;  % Use snr_values field for compatibility
        result.optimal_angle = optimal_angle_rel;  % Relative to RIS normal
        result.optimal_snr = max_directivity;  % Use snr field for compatibility
        result.deflection_angle = optimal_angle_rel;  % Same as optimal in discovery
        result.snr_at_deflection = max_directivity;
        result.incident_angle = incident_angle_rel;  % Relative to RIS normal
        result.target_angle = optimal_angle_abs;  % Absolute beam direction
        result.d_ap_ris = d_ap_ris;
        result.ris_normal_deg = ris_normal_deg;
        result.d_ris_ue = 0;  % Unknown in discovery mode
        result.discovery_mode = true;

    else
        % UE-aware mode: compute SNR at known UE
        ue_pos = ue_pos(:)';
        d_ris_ue = norm(ue_pos - ris_pos);

        vec_ue = ue_pos - ris_pos;
        target_angle_abs = atan2d(vec_ue(2), vec_ue(1));  % UE direction from RIS (absolute)

        % Target angle relative to RIS normal
        target_angle_rel = target_angle_abs - ris_normal_deg;
        while target_angle_rel > 180
            target_angle_rel = target_angle_rel - 360;
        end
        while target_angle_rel < -180
            target_angle_rel = target_angle_rel + 360;
        end

        % Deflection angle = target - incident (both relative to RIS normal)
        deflection_rel = target_angle_rel - incident_angle_rel;
        while deflection_rel > 180
            deflection_rel = deflection_rel - 360;
        end
        while deflection_rel < -180
            deflection_rel = deflection_rel + 360;
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
            % beam_angle is relative to RIS normal
            beam_angle_rel = angles(idx);
            beam_angle_abs = ris_normal_deg + beam_angle_rel;

            % Compute steering phases (using absolute angle)
            phases = -k * (x_pos * cosd(beam_angle_abs) + y_pos * sind(beam_angle_abs));

            % Apply quantization
            if bits > 0
                num_levels = 2^bits;
                phase_step = 2*pi / num_levels;
                phases = round(phases / phase_step) * phase_step;
            end

            % Compute array factor at UE direction (absolute)
            kx_ue = k * cosd(target_angle_abs);
            ky_ue = k * sind(target_angle_abs);

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

        % Find optimal (angles are relative to RIS normal)
        [max_snr, max_idx] = max(snr_values);
        optimal_angle_rel = angles(max_idx);
        optimal_angle_abs = ris_normal_deg + optimal_angle_rel;

        % Find SNR at theoretical deflection angle (also relative)
        [~, deflection_idx] = min(abs(angles - target_angle_rel));
        snr_at_target = snr_values(deflection_idx);

        % Create figure
        figure('Name', 'Beam Angle vs SNR Sweep', 'NumberTitle', 'off', ...
               'Position', [100 100 1400 800], 'Color', 'w');

        % === SNR vs Angle ===
        subplot(2,3,[1,2]);
        plot(angles, snr_values, 'b-', 'LineWidth', 2);
        hold on;
        plot(optimal_angle_rel, max_snr, 'ro', 'MarkerSize', 12, 'MarkerFaceColor', 'r');
        plot(target_angle_rel, snr_at_target, 'm^', 'MarkerSize', 12, 'MarkerFaceColor', 'm');
        xline(target_angle_rel, 'm--', 'LineWidth', 1.5);
        xline(optimal_angle_rel, 'r--', 'LineWidth', 1.5);
        xline(incident_angle_rel, 'g:', 'LineWidth', 1.5);
        hold off;
        grid on;
        xlabel('Beam Steering Angle (degrees from RIS normal)', 'FontSize', 11);
        ylabel('SNR (dB)', 'FontSize', 11);
        title(sprintf('SNR vs Beam Angle (%d-bit, %dx%d array)', bits, N, N), 'FontSize', 13);
        legend('SNR', sprintf('Optimal: %.1f deg (%.1f dB)', optimal_angle_rel, max_snr), ...
               sprintf('Target (UE): %.1f deg (%.1f dB)', target_angle_rel, snr_at_target), ...
               sprintf('Incident (AP): %.1f deg', incident_angle_rel), ...
               'Location', 'best');
        xlim(angle_range);

        % === Array Factor at UE ===
        subplot(2,3,3);
        plot(angles, af_at_ue, 'b-', 'LineWidth', 1.5);
        hold on;
        plot(optimal_angle_rel, af_at_ue(max_idx), 'ro', 'MarkerSize', 10, 'MarkerFaceColor', 'r');
        plot(target_angle_rel, af_at_ue(deflection_idx), 'm^', 'MarkerSize', 10, 'MarkerFaceColor', 'm');
        hold off;
        grid on;
        xlabel('Beam Angle (deg from normal)');
        ylabel('Array Factor at UE (dB)');
        title('Array Factor Response at UE');
        xlim(angle_range);

        % === Geometry Plot ===
        subplot(2,3,4);
        hold on;

        plot(ap_pos(1), ap_pos(2), 'gs', 'MarkerSize', 15, 'MarkerFaceColor', 'g', 'LineWidth', 2);
        plot(ris_pos(1), ris_pos(2), 'r^', 'MarkerSize', 15, 'MarkerFaceColor', 'r', 'LineWidth', 2);
        plot(ue_pos(1), ue_pos(2), 'mo', 'MarkerSize', 15, 'MarkerFaceColor', 'm', 'LineWidth', 2);

        plot([ap_pos(1), ris_pos(1)], [ap_pos(2), ris_pos(2)], 'g--', 'LineWidth', 1.5);
        plot([ris_pos(1), ue_pos(1)], [ris_pos(2), ue_pos(2)], 'm--', 'LineWidth', 1.5);

        % Draw beam direction (optimal)
        beam_len = max(d_ap_ris, d_ris_ue) * 0.5;
        beam_x = ris_pos(1) + beam_len * cosd(optimal_angle_abs);
        beam_y = ris_pos(2) + beam_len * sind(optimal_angle_abs);
        quiver(ris_pos(1), ris_pos(2), beam_x - ris_pos(1), beam_y - ris_pos(2), 0, ...
               'Color', [1 0.3 0], 'LineWidth', 2.5, 'MaxHeadSize', 0.5);

        % Draw RIS normal
        normal_len = beam_len * 0.5;
        normal_x = ris_pos(1) + normal_len * cosd(ris_normal_deg);
        normal_y = ris_pos(2) + normal_len * sind(ris_normal_deg);
        quiver(ris_pos(1), ris_pos(2), normal_x - ris_pos(1), normal_y - ris_pos(2), 0, ...
               'k', 'LineWidth', 1.5, 'MaxHeadSize', 0.3);

        % Draw FoV arc
        arc_radius = beam_len * 0.8;
        arc_angles = linspace(ris_normal_deg - max_steering_deg, ris_normal_deg + max_steering_deg, 50);
        arc_x = ris_pos(1) + arc_radius * cosd(arc_angles);
        arc_y = ris_pos(2) + arc_radius * sind(arc_angles);
        plot(arc_x, arc_y, 'y-', 'LineWidth', 2);

        hold off;
        axis equal;
        grid on;
        xlabel('X (m)');
        ylabel('Y (m)');
        title('Network Geometry');
        legend('AP', 'RIS', 'UE', 'AP to RIS', 'RIS to UE', ...
               sprintf('Beam (%.1f deg)', optimal_angle_abs), sprintf('Normal (%.1f deg)', ris_normal_deg), ...
               'FoV', 'Location', 'best');

        % === Phase Heatmap at Optimal ===
        subplot(2,3,5);
        optimal_phases = -k * (x_pos * cosd(optimal_angle_abs) + y_pos * sind(optimal_angle_abs));
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
        title(sprintf('Phase @ Optimal (%.1f deg rel)', optimal_angle_rel));
        xlabel('Element X');
        ylabel('Element Y');

        % === Phase Heatmap at Target (UE direction) ===
        subplot(2,3,6);
        target_phases = -k * (x_pos * cosd(target_angle_abs) + y_pos * sind(target_angle_abs));
        if bits > 0
            target_phases = round(target_phases / phase_step) * phase_step;
        end
        phases_deg_tgt = mod(rad2deg(target_phases), 360);
        phase_grid_tgt = reshape(phases_deg_tgt, N, N);
        imagesc(phase_grid_tgt);
        colormap(gca, hsv(256));
        colorbar;
        caxis([0 360]);
        axis equal tight;
        title(sprintf('Phase @ Target UE (%.1f deg rel)', target_angle_rel));
        xlabel('Element X');
        ylabel('Element Y');

        % Overall title
        sgtitle(sprintf('Beam Sweep: AP(%.1f,%.1f) to RIS(%.1f,%.1f) to UE(%.1f,%.1f)\nRIS Normal: %.1f deg | Incident: %.1f deg | Target: %.1f deg | Optimal: %.1f deg (all rel to normal)', ...
                ap_pos(1), ap_pos(2), ris_pos(1), ris_pos(2), ue_pos(1), ue_pos(2), ...
                ris_normal_deg, incident_angle_rel, target_angle_rel, optimal_angle_rel), ...
                'FontSize', 11, 'FontWeight', 'bold');

        % Return results (angles relative to RIS normal)
        result.angles = angles;
        result.snr_values = snr_values;
        result.optimal_angle = optimal_angle_rel;  % Relative to RIS normal
        result.optimal_snr = max_snr;
        result.deflection_angle = target_angle_rel;  % Target angle relative to normal
        result.snr_at_deflection = snr_at_target;
        result.incident_angle = incident_angle_rel;  % Relative to RIS normal
        result.target_angle = target_angle_abs;  % Absolute beam direction to UE
        result.d_ap_ris = d_ap_ris;
        result.d_ris_ue = d_ris_ue;
        result.ris_normal_deg = ris_normal_deg;
        result.discovery_mode = false;
    end
end
