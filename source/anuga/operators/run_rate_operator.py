"""Simple water flow example using ANUGA

Water flowing down a channel with a topography that varies with time
"""

#------------------------------------------------------------------------------
# Import necessary modules
#------------------------------------------------------------------------------
from anuga import rectangular_cross
from anuga import Domain
from anuga import Reflective_boundary
from anuga import Dirichlet_boundary
from anuga import Time_boundary


#------------------------------------------------------------------------------
# Setup computational domain
#------------------------------------------------------------------------------
length = 24.
width = 5.
dx = dy = 0.2 #.1           # Resolution: Length of subdivisions on both axes

points, vertices, boundary = rectangular_cross(int(length/dx), int(width/dy),
                                               len1=length, len2=width)
domain = Domain(points, vertices, boundary)
domain.set_name('rate_polygon') # Output name
print domain.statistics()


#------------------------------------------------------------------------------
# Setup initial conditions
#------------------------------------------------------------------------------
def topography(x,y):
    """Complex topography defined by a function of vectors x and y."""

    z = -x/100

    N = len(x)
    for i in range(N):
        # Step
        if 2 < x[i] < 4:
            z[i] += 0.4 - 0.05*y[i]

        # Permanent pole
        #if (x[i] - 8)**2 + (y[i] - 2)**2 < 0.4**2:
        #    z[i] += 1


#        # Dam
#        if 12 < x[i] < 13 and y[i] > 3.0:
#            z[i] += 0.4
#
#        if 12 < x[i] < 13 and y[i] < 2.0:
#            z[i] += 0.4


#        # Dam
#        if 12 < x[i] < 13:
#            z[i] += 0.4

            
    return z


def pole_increment(x,y,t):
    """This provides a small increment to a pole located mid stream
    For use with variable elevation data
    """


    z = 0.0*x
    

    if t<10.0:
        return z
    

    N = len(x)
    for i in range(N):
        # Pole 1
        if (x[i] - 12)**2 + (y[i] - 3)**2 < 0.4**2:
            z[i] += 0.1

    for i in range(N):
        # Pole 2
        if (x[i] - 14)**2 + (y[i] - 2)**2 < 0.4**2:
            z[i] += 0.05

    return z


def pole(t):

    if t<10:
        return 0.0
    elif t>15:
        return 0.0
    else:
        return 0.05


domain.set_quantity('elevation', topography)           # elevation is a function
domain.set_quantity('friction', 0.01)                  # Constant friction
domain.set_quantity('stage', expression='elevation')   # Dry initial condition

#------------------------------------------------------------------------------
# Setup boundary conditions
#------------------------------------------------------------------------------
Bi = Dirichlet_boundary([0.4, 0, 0])          # Inflow
Br = Reflective_boundary(domain)              # Solid reflective wall
Bo = Dirichlet_boundary([-5, 0, 0])           # Outflow

domain.set_boundary({'left': Br, 'right': Br, 'top': Br, 'bottom': Br})

#------------------------------------------------------------------------------
# Evolve system through time
#------------------------------------------------------------------------------
polygon1 = [ [10.0, 0.0], [11.0, 0.0], [11.0, 5.0], [10.0, 5.0] ]
polygon2 = [ [12.0, 2.0], [13.0, 2.0], [13.0, 3.0], [12.0, 3.0] ]

from anuga.operators.rate_operators import Polygonal_rate_operator
from anuga.operators.rate_operators import Circular_rate_operator

op1 = Polygonal_rate_operator(domain, rate=10.0, polygon=polygon2)
op2 = Circular_rate_operator(domain, rate=10.0, radius=0.5, center=(10.0, 3.0))


for t in domain.evolve(yieldstep=0.1, finaltime=40.0):
    domain.print_timestepping_statistics()
    domain.print_operator_timestepping_statistics()

    stage = domain.get_quantity('stage')
    elev  = domain.get_quantity('elevation')
    height = stage - elev

    print 'integral = ', height.get_integral()







