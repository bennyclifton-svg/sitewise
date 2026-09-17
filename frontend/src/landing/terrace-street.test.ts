import { expect, it } from 'vitest'
import { streetRoutes } from './terrace-street'
import { rollerPose } from './terrace-animation'

it('ties every house to the lower sewer and the 400 mm stormwater main', () => {
  const routes = streetRoutes()
  expect(routes.find(r => r.name === '400 mm stormwater main')?.radius).toBe(.2)
  for (let house = 1; house <= 7; house++) {
    const own = routes.filter(r => r.house === house)
    expect(own).toHaveLength(5)
    expect(own.find(r => r.name.includes('sanitary'))?.points.at(-1)?.slice(1)).toEqual([-1.9, 5.8])
    expect(own.find(r => r.name.startsWith('Detention overflow'))?.points.at(-1)?.slice(1)).toEqual([-.75, 6.4])
    expect(own.find(r => r.name.startsWith('Rear pit'))?.points.at(-1)).toEqual(own.find(r => r.name.startsWith('Front pit'))?.points[0])
  }
  expect(routes.filter(r => r.name.startsWith('Overhead power span'))).toHaveLength(4)
  expect(routes.filter(r => r.name.startsWith('Overhead power span')).every(r => r.radius < .01)).toBe(true)
  const feed = routes.find(r => r.name === 'Pole riser and pillar feed')!
  expect(feed.points.at(-1)).toEqual(routes.find(r => r.name === 'Pillar to distribution conduit')?.points[0])
  expect(feed.points[0]).toEqual(routes.find(r => r.name === 'Overhead power span 1')?.points.at(-1))
})

it('lifts roller slats around a continuous track without passing above its headroom', () => {
  for (let index = 0; index < 25; index++) {
    let previous = rollerPose(index, 0)
    for (let lift = .01; lift <= 2.5; lift += .01) {
      const pose = rollerPose(index, lift)
      expect(pose.y).toBeLessThanOrEqual(2.89)
      expect(Math.hypot(pose.y - previous.y, pose.z - previous.z)).toBeLessThan(.011)
      previous = pose
    }
  }
})
