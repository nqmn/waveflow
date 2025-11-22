function plot_ris_geometry(ris_pos, elem_pos, ap_pos, ue_pos, beam_angle, title_str)
    % Plot RIS geometry in 3D
    %
    % Inputs:
    %   ris_pos    - RIS center [x, y, z]
    %   elem_pos   - Element positions (N*N x 3)
    %   ap_pos     - AP position [x, y, z] (optional, empty if not provided)
    %   ue_pos     - UE position [x, y, z] (optional, empty if not provided)
    %   beam_angle - Beam steering angle in degrees (optional)
    %   title_str  - Plot title

    figure('Name', 'RIS Geometry', 'NumberTitle', 'off');
    hold on; grid on;

    % Plot RIS elements
    scatter3(elem_pos(:,1), elem_pos(:,2), elem_pos(:,3), ...
             20, 'b', 'filled', 'DisplayName', 'RIS Elements');

    % Plot RIS center
    scatter3(ris_pos(1), ris_pos(2), ris_pos(3), ...
             100, 'r', 'filled', 'd', 'DisplayName', 'RIS Center');

    % Plot AP if provided
    if ~isempty(ap_pos)
        scatter3(ap_pos(1), ap_pos(2), ap_pos(3), ...
                 150, 'g', 'filled', 's', 'DisplayName', 'AP');
        % Draw line from AP to RIS
        plot3([ap_pos(1), ris_pos(1)], ...
              [ap_pos(2), ris_pos(2)], ...
              [ap_pos(3), ris_pos(3)], 'g--', 'LineWidth', 1.5);
    end

    % Plot UE if provided
    if ~isempty(ue_pos)
        scatter3(ue_pos(1), ue_pos(2), ue_pos(3), ...
                 150, 'm', 'filled', '^', 'DisplayName', 'UE');
        % Draw line from RIS to UE
        plot3([ris_pos(1), ue_pos(1)], ...
              [ris_pos(2), ue_pos(2)], ...
              [ris_pos(3), ue_pos(3)], 'm--', 'LineWidth', 1.5);
    end

    % Draw beam direction if provided
    if ~isempty(beam_angle)
        beam_len = 5;
        beam_end = ris_pos + beam_len * [cosd(beam_angle), sind(beam_angle), 0];
        quiver3(ris_pos(1), ris_pos(2), ris_pos(3), ...
                beam_end(1)-ris_pos(1), beam_end(2)-ris_pos(2), beam_end(3)-ris_pos(3), ...
                0, 'r', 'LineWidth', 2, 'MaxHeadSize', 0.5, 'DisplayName', 'Beam');
    end

    xlabel('X (m)'); ylabel('Y (m)'); zlabel('Z (m)');
    title(title_str);
    legend('Location', 'best');
    view(3);
    axis equal;
    hold off;
end
