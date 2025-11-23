function plot_ris_geometry(ris_pos, elem_pos, ap_positions, ue_positions, beam_angle, title_str, ap_names, ue_names, ris_normal, beam_arc_range)
    % Plot RIS geometry in 3D with all network nodes
    %
    % Inputs:
    %   ris_pos       - RIS center [x, y, z]
    %   elem_pos      - Element positions (N*N x 3)
    %   ap_positions  - AP positions (N_ap x 3) or empty
    %   ue_positions  - UE positions (N_ue x 3) or empty
    %   beam_angle    - Beam steering angle in degrees (optional)
    %   title_str     - Plot title
    %   ap_names      - Cell array of AP names (optional)
    %   ue_names      - Cell array of UE names (optional)
    %   ris_normal    - RIS normal angle in degrees (optional, default 0)
    %   beam_arc_range - [min_angle, max_angle] for beam arc visualization (optional)

    % Handle optional arguments
    if nargin < 7 || isempty(ap_names)
        ap_names = {};
    end
    if nargin < 8 || isempty(ue_names)
        ue_names = {};
    end
    if nargin < 9 || isempty(ris_normal)
        ris_normal = 0;
    end
    if nargin < 10 || isempty(beam_arc_range)
        beam_arc_range = [];
    end

    % Colors for multiple nodes
    ap_colors = [0, 0.7, 0;      % Green
                 0, 0.5, 0.3;    % Teal
                 0.2, 0.8, 0.2]; % Light green
    ue_colors = [0.8, 0, 0.8;    % Magenta
                 0.6, 0, 0.6;    % Purple
                 1, 0.4, 0.7];   % Pink

    figure('Name', 'RIS Network Geometry', 'NumberTitle', 'off', 'Position', [100, 100, 900, 700]);
    hold on; grid on;

    % Plot RIS elements
    scatter3(elem_pos(:,1), elem_pos(:,2), elem_pos(:,3), ...
             20, 'b', 'filled', 'DisplayName', 'RIS Elements');

    % Plot RIS center
    scatter3(ris_pos(1), ris_pos(2), ris_pos(3), ...
             150, 'r', 'filled', 'd', 'DisplayName', 'RIS Center', 'LineWidth', 2);

    % Draw RIS normal direction
    normal_len = 3;
    normal_end = ris_pos + normal_len * [cosd(ris_normal), sind(ris_normal), 0];
    quiver3(ris_pos(1), ris_pos(2), ris_pos(3), ...
            normal_end(1)-ris_pos(1), normal_end(2)-ris_pos(2), normal_end(3)-ris_pos(3), ...
            0, 'k', 'LineWidth', 1.5, 'MaxHeadSize', 0.3, 'DisplayName', 'RIS Normal');

    % Plot all APs
    if ~isempty(ap_positions) && size(ap_positions, 1) > 0
        num_aps = size(ap_positions, 1);
        for i = 1:num_aps
            color_idx = mod(i-1, size(ap_colors, 1)) + 1;
            ap_color = ap_colors(color_idx, :);
            ap_pos = ap_positions(i, :);

            % Get AP name
            if i <= length(ap_names) && ~isempty(ap_names{i})
                ap_label = ap_names{i};
            else
                ap_label = sprintf('AP%d', i);
            end

            scatter3(ap_pos(1), ap_pos(2), ap_pos(3), ...
                     200, ap_color, 'filled', 's', 'DisplayName', ap_label, 'LineWidth', 2);

            % Draw line from AP to RIS
            plot3([ap_pos(1), ris_pos(1)], ...
                  [ap_pos(2), ris_pos(2)], ...
                  [ap_pos(3), ris_pos(3)], '--', 'Color', ap_color, 'LineWidth', 1.5, 'HandleVisibility', 'off');

            % Add text label
            text(ap_pos(1), ap_pos(2), ap_pos(3) + 0.5, ap_label, ...
                 'FontSize', 10, 'FontWeight', 'bold', 'Color', ap_color, 'HorizontalAlignment', 'center');
        end
    end

    % Plot all UEs
    if ~isempty(ue_positions) && size(ue_positions, 1) > 0
        num_ues = size(ue_positions, 1);
        for i = 1:num_ues
            color_idx = mod(i-1, size(ue_colors, 1)) + 1;
            ue_color = ue_colors(color_idx, :);
            ue_pos = ue_positions(i, :);

            % Get UE name
            if i <= length(ue_names) && ~isempty(ue_names{i})
                ue_label = ue_names{i};
            else
                ue_label = sprintf('UE%d', i);
            end

            scatter3(ue_pos(1), ue_pos(2), ue_pos(3), ...
                     200, ue_color, 'filled', '^', 'DisplayName', ue_label, 'LineWidth', 2);

            % Draw line from RIS to UE
            plot3([ris_pos(1), ue_pos(1)], ...
                  [ris_pos(2), ue_pos(2)], ...
                  [ris_pos(3), ue_pos(3)], '--', 'Color', ue_color, 'LineWidth', 1.5, 'HandleVisibility', 'off');

            % Add text label
            text(ue_pos(1), ue_pos(2), ue_pos(3) + 0.5, ue_label, ...
                 'FontSize', 10, 'FontWeight', 'bold', 'Color', ue_color, 'HorizontalAlignment', 'center');
        end
    end

    % Draw beam direction if provided
    if ~isempty(beam_angle)
        beam_len = 5;
        % Beam angle is the absolute direction the beam points
        beam_end = ris_pos + beam_len * [cosd(beam_angle), sind(beam_angle), 0];
        quiver3(ris_pos(1), ris_pos(2), ris_pos(3), ...
                beam_end(1)-ris_pos(1), beam_end(2)-ris_pos(2), beam_end(3)-ris_pos(3), ...
                0, 'Color', [1, 0.3, 0], 'LineWidth', 3, 'MaxHeadSize', 0.5, 'DisplayName', sprintf('Beam (%.1f°)', beam_angle));
    end

    % Draw beam arc (field of view) if provided
    if ~isempty(beam_arc_range) && length(beam_arc_range) >= 2
        arc_radius = 4;
        min_angle = beam_arc_range(1);
        max_angle = beam_arc_range(2);

        % Create arc points
        arc_angles = linspace(min_angle, max_angle, 50);
        arc_x = ris_pos(1) + arc_radius * cosd(arc_angles);
        arc_y = ris_pos(2) + arc_radius * sind(arc_angles);
        arc_z = ones(size(arc_angles)) * ris_pos(3);

        % Draw filled arc (semi-transparent)
        fill3([ris_pos(1), arc_x, ris_pos(1)], ...
              [ris_pos(2), arc_y, ris_pos(2)], ...
              [ris_pos(3), arc_z, ris_pos(3)], ...
              [0.9, 0.9, 0.5], 'FaceAlpha', 0.2, 'EdgeColor', [0.7, 0.7, 0], ...
              'LineWidth', 1, 'DisplayName', sprintf('FoV [%.0f°, %.0f°]', min_angle, max_angle));

        % Draw arc boundary lines
        plot3([ris_pos(1), ris_pos(1) + arc_radius*cosd(min_angle)], ...
              [ris_pos(2), ris_pos(2) + arc_radius*sind(min_angle)], ...
              [ris_pos(3), ris_pos(3)], ':', 'Color', [0.7, 0.7, 0], 'LineWidth', 1.5, 'HandleVisibility', 'off');
        plot3([ris_pos(1), ris_pos(1) + arc_radius*cosd(max_angle)], ...
              [ris_pos(2), ris_pos(2) + arc_radius*sind(max_angle)], ...
              [ris_pos(3), ris_pos(3)], ':', 'Color', [0.7, 0.7, 0], 'LineWidth', 1.5, 'HandleVisibility', 'off');
    end

    % Add RIS label
    text(ris_pos(1), ris_pos(2), ris_pos(3) - 0.8, 'RIS', ...
         'FontSize', 11, 'FontWeight', 'bold', 'Color', 'r', 'HorizontalAlignment', 'center');

    xlabel('X (m)', 'FontSize', 11);
    ylabel('Y (m)', 'FontSize', 11);
    zlabel('Z (m)', 'FontSize', 11);
    title(title_str, 'FontSize', 12);
    legend('Location', 'best', 'FontSize', 9);
    view(3);
    axis equal;

    % Set nice viewing angle
    view(45, 30);

    hold off;
end
