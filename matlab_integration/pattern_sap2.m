function pattern(plane, freq, r_src, theta_src, theta_rcv, phi_rcv, nx, ny, dx, dy, mode, bit)
%% ============================================================
% DEFAULT PARAMETERS — EXACTLY MATCH PYTHON CALL
%% ============================================================
if nargin < 1, plane = 0; end
if nargin < 2, freq = 5.8e9; end
if nargin < 3, r_src = 0.45; end
if nargin < 4, theta_src = 0; end
if nargin < 5, theta_rcv = 50; end
if nargin < 6, phi_rcv = 0; end
if nargin < 7, nx = 16; end
if nargin < 8, ny = 16; end
if nargin < 9, dx = 0.02585; end
if nargin < 10, dy = 0.02585; end
if nargin < 11, mode = 0; end
if nargin < 12, bit = 1; end

%% ============================================================
% CONSTANTS
%% ============================================================
c = physconst('LightSpeed');
k = 2*pi*freq/c;

theta_src = deg2rad(theta_src);
theta_rcv = deg2rad(theta_rcv);
phi_rcv   = deg2rad(phi_rcv);

%% ============================================================
% ELEMENT COORDINATES (EXACT PYTHON)
%% ============================================================
N = nx * ny;
lim = (nx - 1)/2 * dx;
coor = linspace(-lim, lim, nx);

[X, Y] = meshgrid(coor, coor);
r_c = [X(:), Y(:), zeros(N,1)];

%% ============================================================
% SOURCE POSITION (EXACT PYTHON)
%% ============================================================
x_s = r_src * sin(theta_src) * cos(0);
y_s = r_src * sin(theta_src) * sin(0);
z_s = r_src * cos(theta_src);
r_src_cart = [x_s, y_s, z_s];

%% ============================================================
% STEERING VECTOR (EXACT PYTHON)
%% ============================================================
u = [ sin(theta_rcv)*cos(phi_rcv), ...
      sin(theta_rcv)*sin(phi_rcv), ...
      cos(theta_rcv) ];

%% ============================================================
% SOURCE PHASE (EXACT PYTHON)
%% ============================================================
if plane == 1
    phase_src = mod(-k * (r_c * u'), 2*pi);
else
    dist = vecnorm(r_src_cart - r_c, 2, 2);
    phase_src = mod(k*dist - k*(r_c*u'), 2*pi);
end

phase_src = reshape(phase_src, nx, ny);
phase_src_deg = rad2deg(phase_src);

%% ============================================================
% QUANTIZATION (EXACT PYTHON)
%% ============================================================
intervals = linspace(0, 2*pi, 2^bit + 1);
phase_src_dg = discretize(phase_src, intervals) - 1;

%% ============================================================
% OAM PHASE (EXACT PYTHON)
%% ============================================================
phase_oam = mod(mode * atan2(r_c(:,2), r_c(:,1)), 2*pi);
phase_oam = reshape(phase_oam, nx, ny);
phase_oam_deg = rad2deg(phase_oam);
phase_oam_dg = discretize(phase_oam, intervals) - 1;

%% ============================================================
% TOTAL PHASE (EXACT PYTHON)
%% ============================================================
phase_ms = mod(phase_src + phase_oam, 2*pi);
phase_ms_deg = rad2deg(phase_ms);
phase_ms_dg  = discretize(phase_ms, intervals) - 1;

%% ============================================================
% PLOTTING (SAME AS PYTHON)
%% ============================================================
figure('Position',[100 100 1400 600])

subplot(2,3,1); pcolor(phase_src_deg); shading flat; colormap jet;
title('Source Phase (deg)'); colorbar;

subplot(2,3,2); pcolor(phase_oam_deg); shading flat; colormap jet;
title('OAM Phase (deg)'); colorbar;

subplot(2,3,3); pcolor(phase_ms_deg); shading flat; colormap jet;
title('Total Phase (deg)'); colorbar;

subplot(2,3,4); pcolor(phase_src_dg); shading flat;
title(sprintf('Quantized Source (%d-bit)', bit)); colorbar;

subplot(2,3,5); pcolor(phase_oam_dg); shading flat;
title(sprintf('Quantized OAM (%d-bit)', bit)); colorbar;

subplot(2,3,6); pcolor(phase_ms_dg); shading flat;
title(sprintf('Quantized Total (%d-bit)', bit)); colorbar;

%% ============================================================
%              3D FAR-FIELD BEAMPATTERN (PYTHON-MATCHED)
%% ============================================================

figure('Name','3D Far-field Beampattern','NumberTitle','off',...
       'Position',[100 100 1200 900]);

% Compute element weights from total phase (same as Python)
%w = exp(1j * phase_ms(:));   % N x 1

% 1-bit quantization: values 0 or π
quantized_phase = intervals(phase_ms_dg + 1);   % lookup bin center
w = exp(1j * quantized_phase(:));               % use quantized weights

% Angular grid
el = deg2rad(0:0.5:90);          % elevation (RIS radiates forward hemisphere)
az = deg2rad(-180:1:180);        % full azimuth
[AZ, EL] = meshgrid(az, el);     % EL, AZ = size [181 x 361]

% Direction cosines
ux = sin(EL) .* cos(AZ);
uy = sin(EL) .* sin(AZ);
% uz = cos(EL);  % not needed (RIS elements on z=0)

% Array factor
AF = zeros(size(EL));
for i = 1:N
    AF = AF + w(i) .* exp(1j * k * (r_c(i,1)*ux + r_c(i,2)*uy));
end

AF_lin = abs(AF);
AF_dB  = 20*log10(AF_lin/max(AF_lin(:)) + 1e-12);

%% Convert spherical → Cartesian (for plotting)
R = AF_lin ./ max(AF_lin(:));  % normalized radius
X3 = R .* cos(EL) .* cos(AZ);
Y3 = R .* cos(EL) .* sin(AZ);
Z3 = R .* sin(EL);

%% --- Draw 3D radiation surface ---
surf(X3, Y3, Z3, AF_dB, 'EdgeColor','none');
colormap(jet);
colorbar; caxis([-30 0]);
hold on;

%% --- RIS plane (gray) ---
planeSize = max(R(:))*0.4;
[xp, yp] = meshgrid(linspace(-planeSize,planeSize,40));
zp = -0.01 * ones(size(xp));
surf(xp, yp, zp, 'FaceAlpha',0.15,'FaceColor',[0.5 0.5 0.5], 'EdgeColor','none');

%% --- Incoming arrow (source -> RIS) ---
src = [0 0 r_src];   % source directly above RIS
plot3([src(1) 0],[src(2) 0],[src(3) 0], '--', ...
    'Color',[0 0.4 0.9],'LineWidth',2);
quiver3(0,0,r_src*0.6, 0,0,-0.2, 'Color',[0 0.4 0.9], ...
        'LineWidth',2,'MaxHeadSize',3);
text(src(1),src(2),src(3)+0.05,'Source','FontSize',12,'Color',[0 0.4 0.9]);

%% --- Outgoing arrow (RIS -> θ_rcv direction) ---
vx = cos(theta_rcv)*cos(phi_rcv);
vy = cos(theta_rcv)*sin(phi_rcv);
vz = sin(theta_rcv);

quiver3(0,0,0, vx*0.7,vy*0.7,vz*0.7, ...
    'LineWidth',2.5,'Color',[1 0.3 0],'LineStyle','--','MaxHeadSize',2.5);
text(vx*0.8,vy*0.8,vz*0.8, sprintf('Steer = %.1f°', rad2deg(theta_rcv)), ...
     'FontSize',12,'Color',[1 0.3 0]);

%% --- Main lobe marker ---
[~, idxMax] = max(AF_lin(:));
xm = X3(idxMax); ym = Y3(idxMax); zm = Z3(idxMax);
plot3(xm, ym, zm, 'ko', 'MarkerFaceColor','y','MarkerSize',8);

%% Formatting
title('3D Far-field Beampattern');
xlabel('X'); ylabel('Y'); zlabel('Z');
axis equal; grid on;
lighting gouraud; camlight headlight;
view(35,25);
rotate3d on;
hold off;


end
