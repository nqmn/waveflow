% example_4_ris_phase_farfield_cst_style.m
% Complete RIS phase + far-field visualization with CST-style annotations,
% incoming dashed arrow (source -> RIS), outgoing dashed arrow (RIS -> steer),
% E/H-plane guides, main-lobe detection, optional horn marker and export hook.
%
% Related paper: A Novel RIS-Aided Indoor Localization in Single Access Point
%   Scenarios via Generative AI
%
% Run simply:
%   >> example_4_ris_phase_farfield_cst_style
%
% Optional overrides:
%   >> example_4_ris_phase_farfield_cst_style(plane, freq, r_src_val, theta_src, theta_rcv, phi_rcv, nx, ny, dx, dy, mode, bit)
%
function example_4_ris_phase_farfield_cst_style(plane, freq, r_src_val, theta_src, theta_rcv, phi_rcv, ...
                 nx_in, ny_in, dx, dy, mode, bit)

%% =========================
% Default parameters
% ==========================
if nargin < 1, plane = 0; end
if nargin < 2, freq = 5.8e9; end
if nargin < 3, r_src_val = 0.45; end      % source height (m)
if nargin < 4, theta_src = 0; end        % source elevation (deg) (not used for A)
if nargin < 5, theta_rcv = 10; end       % steering elevation (deg)
if nargin < 6, phi_rcv = 0; end          % steering azimuth (deg)
if nargin < 7, nx_in = 16; end
if nargin < 8, ny_in = 16; end
if nargin < 9, dx = 0.02585; end
if nargin < 10, dy = 0.02585; end
if nargin < 11, mode = 0; end
if nargin < 12, bit = 1; end

% Visualization toggles
addHorn = true;          % draw a simple horn marker at the source
exportPNG = false;       % set true to auto-save PNG of final 3D view

%% =========================
% Constants and geometry
% ==========================
c = physconst('LightSpeed');
k = 2*pi*freq/c;

% convert to radians
theta_src = deg2rad(theta_src);
theta_rcv = deg2rad(theta_rcv);
phi_rcv   = deg2rad(phi_rcv);

nx = nx_in; ny = ny_in; N = nx*ny;
intervals = linspace(0,2*pi,2^bit+1);

% coordinates of unit elements (centered on origin on z=0 plane)
lim = (nx - 1)/2 * dx;
coor = linspace(-lim, lim, nx);
[Xel, Yel] = meshgrid(coor, coor);
r_c = [Xel(:), Yel(:), zeros(N,1)];      % N x 3

% source location (option A: directly above RIS center)
r_src = [0, 0, r_src_val];  % x,y,z

% steering unit vector (outgoing)
u_steer = [cos(theta_rcv)*cos(phi_rcv), cos(theta_rcv)*sin(phi_rcv), sin(theta_rcv)];

%% =========================
% Phase calculations
% ==========================
if plane == 1
    phase_src = mod(-k * (r_c * u_steer'), 2*pi);
else
    dist = vecnorm(r_src - r_c, 2, 2);     % distance from source to each element
    phase_src = mod(k*dist - k*(r_c * u_steer'), 2*pi);
end
phase_src = reshape(phase_src, nx, ny);
phase_src_deg = rad2deg(phase_src);
phase_src_dg = discretize(phase_src, intervals) - 1;

% OAM contribution
angle_oam = atan2(r_c(:,2), r_c(:,1));
phase_oam = mod(mode * angle_oam, 2*pi);
phase_oam = reshape(phase_oam, nx, ny);
phase_oam_deg = rad2deg(phase_oam);
phase_oam_dg = discretize(phase_oam, intervals) - 1;

% total phase
phase_ms = mod(phase_src + phase_oam, 2*pi);
phase_ms_deg = rad2deg(phase_ms);
phase_ms_dg = discretize(phase_ms, intervals) - 1;

%% =========================
% Far-field (forward hemisphere)
% ==========================
% Elevation TH measured from the array normal direction (0 = broadside/zenith).
% Using elevation in [0, 90] (forward hemisphere) and full azimuth [-180,180].
el_deg = 0:0.5:90;                 % elevation degrees (0..90)
az_deg = -180:1:180;               % azimuth degrees
TH = deg2rad(el_deg);              % 1 x nTh
PH = deg2rad(az_deg);              % 1 x nPh

% Create 2D grids (size: nPh x nTh) where rows = azimuth, cols = elevation
[AZG, ELG] = meshgrid(PH, TH);     % AZG: nTh x nPh? transpose later
% For consistency with later indexing, build as:
[EL, AZ] = meshgrid(TH, PH);       % EL (nPh x nTh), AZ (nPh x nTh)

% direction cosines (plane wave propagation vector components)
ux = sin(EL) .* cos(AZ);   % nPh x nTh
uy = sin(EL) .* sin(AZ);
% uz = cos(EL);  % not used because elements at z=0

w = exp(1j * phase_ms(:)); % N x 1

% compute AF over grid
AF = zeros(size(EL));      % nPh x nTh
for i = 1:N
    AF = AF + w(i) .* exp(1j * k * ( r_c(i,1) * ux + r_c(i,2) * uy ));
end

% apply element pattern to suppress edge/backwards effects (forward-only emphasis)
% elementPattern ranges [0..1], stronger exponent -> stronger forward-only bias
elementPattern = max(cos(EL), 0).^3;   % simple directive patch-like element
AF = AF .* elementPattern;

AF_lin = abs(AF);
AF_dB = 20*log10(AF_lin / max(AF_lin(:)) + 1e-12);

%% =========================
% 2D Phase maps + 2D beampattern plot
% ==========================
fig1 = figure('Name','Phase maps & 2D beampattern','NumberTitle','off','Position',[40 40 1600 900]);

subplot(3,3,1);
pcolor(Xel, Yel, phase_src_deg); shading flat; axis equal;
title('Source Phase (deg)'); colorbar;

subplot(3,3,2);
pcolor(Xel, Yel, phase_oam_deg); shading flat; axis equal;
title('OAM Phase (deg)'); colorbar;

subplot(3,3,3);
pcolor(Xel, Yel, phase_ms_deg); shading flat; axis equal;
title('True Phase (deg)'); colorbar;

subplot(3,3,4);
pcolor(Xel, Yel, phase_src_dg); shading flat; axis equal;
title(sprintf('Quantized Source (%d-bit)', bit)); colorbar;

subplot(3,3,5);
pcolor(Xel, Yel, phase_oam_dg); shading flat; axis equal;
title(sprintf('Quantized OAM (%d-bit)', bit)); colorbar;

subplot(3,3,6);
pcolor(Xel, Yel, phase_ms_dg); shading flat; axis equal;
title(sprintf('Quantized Total (%d-bit)', bit)); colorbar;

subplot(3,3,[7 8 9]);
imagesc(az_deg, el_deg, AF_dB'); axis xy;
xlabel('Azimuth (deg)'); ylabel('Elevation (deg)');
title('Far-Field Beampattern (2D, dB)');
colorbar; caxis([-40 0]);

%% =========================
% 3D CST-style Visualization with annotations
% ==========================
fig2 = figure('Name','3D CST-style Beampattern','NumberTitle','off','Position',[80 60 1300 1000]);

% Build 3D coordinates for surface (must be same size as AF_dB)
% Use spherical-to-cartesian with radius = normalized AF magnitude
R = AF_lin ./ max(AF_lin(:));     % nPh x nTh

% Coordinates: X = R*cos(el)*cos(az), Y = R*cos(el)*sin(az), Z = R*sin(el)
% Note: here EL and AZ are nPh x nTh
X3 = R .* cos(EL) .* cos(AZ);
Y3 = R .* cos(EL) .* sin(AZ);
Z3 = R .* sin(EL);

% Surface: color by AF_dB
hSurf = surf(X3, Y3, Z3, AF_dB, 'EdgeColor','none', 'FaceLighting','gouraud');
colormap(jet); caxis([-40 0]);
cb = colorbar; cb.Label.String = 'dB';
hold on;

% translucent RIS plane (slightly below z=0 for visual separation)
planeHalf = max(R(:)) * 0.45;
[Xp, Yp] = meshgrid(linspace(-planeHalf, planeHalf, 40));
Zp = zeros(size(Xp)) - 0.02;
surf(Xp, Yp, Zp, 'FaceAlpha', 0.12, 'EdgeColor','none', 'FaceColor', [0.6 0.6 0.6]);

% mark element centers on RIS (optional small dots)
scatter3(r_c(:,1), r_c(:,2), r_c(:,3)+0.002, 10, 'k', 'filled');

% ---------- Incoming dashed arrow (Source -> RIS) ----------
srcPos = r_src;      % [0 0 r_src_val]
risCenter = [0 0 0];

% dashed line
plot3([srcPos(1), risCenter(1)], [srcPos(2), risCenter(2)], [srcPos(3), risCenter(3)], ...
    '--', 'Color', [0 0.45 0.95], 'LineWidth', 2.2);

% arrowhead near RIS (pointing to RIS)
v_in = (risCenter - srcPos); v_in = v_in / norm(v_in);
arrowPos = risCenter + 0.12*(srcPos - risCenter);
quiver3(arrowPos(1), arrowPos(2), arrowPos(3), v_in(1)*0.07, v_in(2)*0.07, v_in(3)*0.07, ...
    'LineWidth',2.2, 'Color', [0 0.45 0.95], 'MaxHeadSize', 3, 'AutoScale','off');

% source label (and optional horn)
text(srcPos(1), srcPos(2), srcPos(3)+0.03, 'Source', 'Color', [0 0.45 0.95], 'FontSize',12, 'FontWeight','bold');

if addHorn
    % simple cone horn marker (approximate)
    [hc_x,hc_y,hc_z] = cylinder([0.0 0.02], 8);
    hc_z = hc_z * 0.05;  % height
    hc_x = hc_x * 0.02; hc_y = hc_y * 0.02;
    surf(hc_x + srcPos(1), hc_y + srcPos(2), hc_z + srcPos(3)-0.01, 'FaceColor', [0.4 0.4 0.4], 'EdgeColor', 'none');
end

% ---------- Outgoing dashed arrow (RIS -> steered beam) ----------
vx = u_steer(1); vy = u_steer(2); vz = u_steer(3);
quiver3(0,0,0, vx*0.7, vy*0.7, vz*0.7, 'LineWidth', 3, 'Color', [1 0.45 0], 'LineStyle', '--', 'MaxHeadSize', 2.5, 'AutoScale','off');
text(vx*0.78, vy*0.78, vz*0.78, sprintf('Steered Beam (\\theta=%.1f\\circ)', rad2deg(theta_rcv)), ...
    'Color', [0.7 0.18 0.05], 'FontSize',12, 'FontWeight','bold');

% ---------- detect main lobe peak and annotate ----------
[~, idxMax] = max(AF_lin(:));
% convert linear index to subscripts
[rowMax, colMax] = ind2sub(size(AF_lin), idxMax);
% coordinates at peak
xp = X3(idxMax); yp = Y3(idxMax); zp = Z3(idxMax);
plot3(xp, yp, zp, 'ko', 'MarkerFaceColor', 'y', 'MarkerSize', 8);
% label with numeric peak gain
text(xp, yp, zp + 0.03, sprintf('Peak = %.1f dB', AF_dB(idxMax)), 'FontWeight','bold');

% ---------- E-plane and H-plane guides (plot as lines for clarity) ----------
% E-plane: phi = 0 (closest azimuth index)
[~, az0Idx] = min(abs(az_deg - 0));
Xe = squeeze(X3(az0Idx, :));
Ye = squeeze(Y3(az0Idx, :));
Ze = squeeze(Z3(az0Idx, :));
% plot E-plane curve slightly offset alpha for visibility
plot3(Xe, Ye, Ze, 'k-', 'LineWidth', 1.1);

% H-plane: elevation at nearest steering elevation index (cut at theta_rcv)
[~, elIdx] = min(abs(el_deg - rad2deg(theta_rcv)));
Xh = squeeze(X3(:, elIdx));
Yh = squeeze(Y3(:, elIdx));
Zh = squeeze(Z3(:, elIdx));
plot3(Xh, Yh, Zh, 'k-', 'LineWidth', 1.1);

% ---------- θ and φ guide arcs (CST-like) ----------
arcR = max(R(:)) * 1.05;
tArc = linspace(0, pi/2, 120);
plot3(arcR*cos(tArc), zeros(size(tArc)), arcR*sin(tArc), 'k--', 'LineWidth', 0.9);
text(arcR*0.65, 0, arcR*0.65, '\theta', 'FontSize',12);
% phi arc near ground plane
pArc = linspace(-pi, pi, 200);
plot3(arcR*0.02*ones(size(pArc)), arcR*cos(pArc), arcR*0.02*ones(size(pArc)), 'k--', 'LineWidth', 0.9);
text(0, arcR*0.8, 0, '\phi', 'FontSize',12);

% ---------- final formatting ----------
xlabel('X'); ylabel('Y'); zlabel('Z');
title(sprintf('3D Far-Field Beampattern with Source & Steering (Steer %.1f°)', rad2deg(theta_rcv)));
axis equal;
grid on; box on;
lighting gouraud;
camlight headlight;
view(35, 28);
rotate3d on;

hold off;

% optional export
if exportPNG
    drawnow;
    fname = sprintf('RIS_beam_steer_theta%02d.png', round(rad2deg(theta_rcv)));
    export_fig = exist('export_fig', 'file'); %#ok<EXIST>
    if export_fig
        export_fig(fname, '-png', '-m2');
    else
        saveas(gcf, fname);
    end
    fprintf('Saved figure: %s\n', fname);
end

end


%% Helper: spherical -> cart (kept for completeness; not used externally)
function xyz = sph2cart_mat(r, theta, phi)
x = r .* sin(theta) .* cos(phi);
y = r .* sin(theta) .* sin(phi);
z = r .* cos(theta);
xyz = [x, y, z];
end
