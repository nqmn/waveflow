function show_phase_heatmap(phases_deg, N, title_str, cmap, show_quant, bits)
    % Display RIS phase distribution as heatmap
    %
    % Inputs:
    %   phases_deg  - NxN matrix of phases in degrees [0, 360)
    %   N           - Array size
    %   title_str   - Plot title
    %   cmap        - Colormap name ('hsv', 'jet', 'parula', etc.)
    %   show_quant  - Show quantization levels (boolean)
    %   bits        - Quantization bits

    figure('Name', 'Phase Heatmap', 'NumberTitle', 'off');

    imagesc(phases_deg);
    colormap(cmap);
    cb = colorbar;
    cb.Label.String = 'Phase (degrees)';
    caxis([0 360]);

    xlabel('Column Index');
    ylabel('Row Index');
    title(title_str);
    axis equal tight;

    % Add quantization info text if requested
    if show_quant && bits > 0
        num_levels = 2^bits;
        phase_step = 360 / num_levels;

        % Add annotation showing quantization info
        text(0.02, 0.98, sprintf('%d-bit quantization\n%d levels (%.1f deg step)', ...
             bits, num_levels, phase_step), ...
             'Units', 'normalized', 'VerticalAlignment', 'top', ...
             'BackgroundColor', 'white', 'EdgeColor', 'black', ...
             'FontSize', 9);

        % Draw horizontal lines on colorbar to show quantization levels
        hold on;
        for level = 1:(num_levels-1)
            phase_val = level * phase_step;
            yline_val = phase_val / 360 * N;
            % This is approximate visualization
        end
        hold off;
    end
end
