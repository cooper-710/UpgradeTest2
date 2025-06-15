
import * as THREE from 'three';

let scene, camera, renderer, clock;
let ball, trail, mixer;
let animationId;
let pitchData = {};
let pitchTrail = [];
let pitchGroup = new THREE.Group();
let isPaused = false;
let showTrail = false;

// Constants
const PLATE_Y = -60.5;
const PITCH_DURATION = 0.45;
const PITCH_TYPE_COLORS = {
    'FF': 0xff0000, // Red
    'SL': 0x0000ff, // Blue
    'CH': 0x00ff00, // Green
    'CU': 0xffff00, // Yellow
    'SI': 0xffa500, // Orange
    'KC': 0x4b0082  // Indigo
};

function initScene() {
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, -65, 3);
    camera.lookAt(0, -60.5, 3);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.body.appendChild(renderer.domElement);

    clock = new THREE.Clock();

    const ambient = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambient);

    const directional = new THREE.DirectionalLight(0xffffff, 0.8);
    directional.position.set(0, 0, 50);
    scene.add(directional);

    const zone = new THREE.Mesh(
        new THREE.BoxGeometry(1.5, 0.01, 2),
        new THREE.MeshBasicMaterial({ color: 0x000000, wireframe: true })
    );
    zone.position.set(0, PLATE_Y, 3.0);
    scene.add(zone);

    scene.add(pitchGroup);
}

function loadPitchData(json) {
    pitchData = json;
    const teamSelect = document.getElementById('teamSelect');
    teamSelect.innerHTML = '<option disabled selected>Select Team</option>';
    for (const team in pitchData) {
        const opt = document.createElement('option');
        opt.value = team;
        opt.innerText = team;
        teamSelect.appendChild(opt);
    }

    teamSelect.addEventListener('change', () => {
        const pitcherSelect = document.getElementById('pitcherSelect');
        pitcherSelect.innerHTML = '<option disabled selected>Select Pitcher</option>';
        for (const pitcher in pitchData[teamSelect.value]) {
            const opt = document.createElement('option');
            opt.value = pitcher;
            opt.innerText = pitcher;
            pitcherSelect.appendChild(opt);
        }
    });

    document.getElementById('pitcherSelect').addEventListener('change', () => {
        startPitchAnimation();
    });

    document.getElementById('trailCheckbox').addEventListener('change', e => {
        showTrail = e.target.checked;
    });

    document.getElementById('replayBtn').addEventListener('click', () => {
        startPitchAnimation();
    });

    document.getElementById('pauseBtn').addEventListener('click', () => {
        isPaused = !isPaused;
    });
}

function createBall(pitchType) {
    const group = new THREE.Group();
    const geometry = new THREE.SphereGeometry(0.145, 32, 32);
    const color = PITCH_TYPE_COLORS[pitchType] || 0xffffff;
    const material1 = new THREE.MeshStandardMaterial({ color: 0xffffff });
    const material2 = new THREE.MeshStandardMaterial({ color });

    const half = new THREE.Mesh(geometry, material1);
    half.rotation.y = Math.PI / 2;
    const stripe = new THREE.Mesh(geometry, material2);
    stripe.scale.x = 0.5;
    stripe.position.x = 0.0725;
    group.add(half);
    group.add(stripe);
    return group;
}

function startPitchAnimation() {
    cancelAnimationFrame(animationId);
    pitchGroup.clear();
    pitchTrail.forEach(p => scene.remove(p));
    pitchTrail = [];

    const team = document.getElementById('teamSelect').value;
    const pitcher = document.getElementById('pitcherSelect').value;
    const pitchKey = Object.keys(pitchData[team][pitcher])[0]; // Just get one for demo
    const pitch = pitchData[team][pitcher][pitchKey];

    const x0 = pitch.release_pos_x;
    const y0 = PLATE_Y + pitch.release_extension;
    const z0 = pitch.release_pos_z;
    const vx0 = pitch.vx0;
    const vy0 = pitch.vy0;
    const vz0 = pitch.vz0;
    const ax = pitch.ax;
    const ay = pitch.ay;
    const az = pitch.az;

    const ball = createBall(pitch.pitch_type);
    ball.position.set(x0, y0, z0);
    pitchGroup.add(ball);

    clock.start();

    function animate() {
        if (isPaused) {
            animationId = requestAnimationFrame(animate);
            return;
        }

        const t = clock.getElapsedTime();
        if (t > PITCH_DURATION) return;

        const x = x0 + vx0 * t + 0.5 * ax * t * t;
        const y = y0 + vy0 * t + 0.5 * ay * t * t;
        const z = z0 + vz0 * t + 0.5 * az * t * t;

        ball.position.set(x, y, z);

        if (showTrail) {
            const dot = new THREE.Mesh(
                new THREE.SphereGeometry(0.02, 8, 8),
                new THREE.MeshBasicMaterial({ color: 0x888888 })
            );
            dot.position.set(x, y, z);
            scene.add(dot);
            pitchTrail.push(dot);
        }

        renderer.render(scene, camera);
        animationId = requestAnimationFrame(animate);
    }

    animate();
}

export { initScene, loadPitchData };
