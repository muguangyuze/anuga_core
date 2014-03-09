"""
Erosion operators


"""

__author__="steve"
__date__ ="$09/03/2012 4:46:39 PM$"



import numpy as num


from anuga import Domain
from anuga import Quantity
from anuga.operators.base_operator import Operator
from anuga import Region


class Erosion_operator(Operator, Region):
    """
    Simple erosion operator in a region (careful to maintain continuitiy of elevation)

    indices: None == all triangles, Empty list [] no triangles

    threshold: Impose erosion if || momentum || > threshold
    base: Allow erosion down to base level

    """

    def __init__(self,
                 domain,
                 threshold= 0.0,
                 base=0.0,
                 indices=None,
                 polygon=None,
                 center=None,
                 radius=None,
                 description = None,
                 label = None,
                 logging = False,
                 verbose = False):


        Operator.__init__(self, domain, description, label, logging, verbose)



        Region.__init__(self, domain,
                        indices=indices,
                        polygon=polygon,
                        center=center,
                        radius=radius,
                        verbose=verbose)

        #------------------------------------------
        # Local variables
        #------------------------------------------
        self.threshold = threshold
        self.base = base


        #------------------------------------------
        # Extra aliases for changing elevation at
        # vertices and edges
        #------------------------------------------
        self.elev_v  = self.domain.quantities['elevation'].vertex_values
        self.elev_e = self.domain.quantities['elevation'].edge_values

        #------------------------------------------
        # Need to turn off this optimization as it
        # doesn't fixup the relationship between
        # bed and stage vertex values in dry region
        #------------------------------------------
        self.domain.optimise_dry_cells = 0

        #-----------------------------------------
        # Extra structures to support maintaining
        # continuity of elevation
        #-----------------------------------------
        self.setup_node_structures()

        #-----------------------------------------
        # Some extras for reporting
        #-----------------------------------------
        self.max_change = 0
        
        

    def update_quantities(self):
        """Update the vertex values of the quantities to model erosion
        """

        t = self.get_time()
        dt = self.get_timestep()


        updated = True

        if self.indices is None:

            #--------------------------------------
            # Update all three vertices for each cell
            #--------------------------------------
            self.elev_c[:] = self.elev_c + 0.0

        else:

            #--------------------------------------
            # Update all three vertices for each cell
            # associated with self.indices
            #--------------------------------------
            ind = self.indices
            m = num.sqrt(self.xmom_c[ind]**2 + self.ymom_c[ind]**2)
            
            if self.domain.flow_algorithm == 'DE1':
                m = num.where(m>self.threshold, m, 0.0)
    
                de = m*dt
                height = self.stage_c[ind] - self.elev_c[ind]
                self.elev_c[ind] = num.maximum(self.elev_v[ind] - de, self.base)
                self.stage_c[ind] = self.elev_c[ind] + height
            else:
                m = num.vstack((m,m,m)).T  # Stack up m to apply to vertices
                m = num.where(m>self.threshold, m, 0.0)
    
                de = m*dt
                self.elev_v[ind] = num.maximum(self.elev_v[ind] - de, self.base)

            self.max_change = num.max(de)

        return updated




    def __call__(self):
        """
        Apply rate to those triangles defined in indices

        indices == [], then don't apply anywhere
        indices == None, then apply everywhere
        otherwise apply for the specific indices
        """


        if self.indices is []:
            return

        #------------------------------------------
        # Apply changes to elevation values
        # via the update_quantites routine
        #------------------------------------------
        if not self.update_quantities():
            return


        #------------------------------------------
        # Cleanup elevation and stage quantity values
        #-----------------------------------------
        self.clean_up_elevation_stage()
        
        
        
        
    def clean_up_elevation_stage(self):
        
        #----------------------------------------------
        # Don't need to clean up if using discontinuous
        # elevation
        #----------------------------------------------
        if self.domain.flow_algorithm == 'DE1':
            return 
        
        
        #-----------------------------------------------
        # Clean up to conserve volume and make elevation 
        # continuous
        #-----------------------------------------------
        if self.indices is None:


            #--------------------------------------
            # Make elevation continuous and clean up
            # stage values to ensure conservation
            #--------------------------------------
            height_c = self.stage_c - self.elev_c
            self.domain.quantities['elevation'].smooth_vertex_values()
            self.domain.quantities['elevation'].interpolate()
            self.stage_c[:] = self.elev_c +  height_c


        else:

            #--------------------------------------
            # Make elevation continuous and clean up
            # stage values to ensure conservation
            #--------------------------------------
            height_c = self.stage_c[self.vols] - self.elev_c[self.vols]
            for nid in self.node_ids:
                non = self.domain.number_of_triangles_per_node[nid]

                vid = num.arange(self.node_index[nid], self.node_index[nid+1],dtype=num.int)
                vidd = self.domain.vertex_value_indices[vid]

                self.elev_v[vidd/3,vidd%3] = num.sum(self.elev_v[vidd/3,vidd%3])/non


            #--------------------------------------
            # clean up the centroid values and edge values
            #--------------------------------------
            self.elev_c[self.vols] = num.mean(self.elev_v[self.vols],axis=1)

            self.elev_e[self.vols,0] = 0.5*(self.elev_v[self.vols,1]+ self.elev_v[self.vols,2])
            self.elev_e[self.vols,1] = 0.5*(self.elev_v[self.vols,2]+ self.elev_v[self.vols,0])
            self.elev_e[self.vols,2] = 0.5*(self.elev_v[self.vols,0]+ self.elev_v[self.vols,1])

            self.stage_c[self.vols] = self.elev_c[self.vols] +  height_c




    def parallel_safe(self):
        """Operator is applied independently on each cell and
        so is parallel safe.
        """
        return False

    def statistics(self):

        message = self.label + ': Erosion_operator'
        message = message + ' on triangles '+ str(self.indices)
        return message


    def timestepping_statistics(self):
        from anuga import indent

        message  = indent + self.label + ': Erosion_operator, time '
        message += str(self.get_time())+ ' max(Delta Elev) '+ str(self.max_change)
        return message


    def dump_triangulation(self):
        # Get vertex coordinates, partition full and ghost triangles based on self.tri_full_flag

        try:
            import matplotlib
            #matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.tri as tri
        except:
            print "Couldn't import module from matplotlib, probably you need to update matplotlib"
            raise

        domain = self.domain

        vertices = domain.get_vertex_coordinates()
        #vertices = vertices.reshape((480,3,2))
        nodes = domain.get_nodes()
        Z = domain.get_quantity('elevation').get_values(location='unique vertices')
        #stage.shape = (1200, )

        fx = nodes[:,0]
        fy = nodes[:,1]
        #gx = vertices[ghost_mask,0]
        #gy = vertices[ghost_mask,1]



        ## Plot full triangles
        n = int(len(fx)/3)
        #triang = num.array(range(0,3*n))
        triang = domain.get_triangles()
        #triang.shape = (n, 3)

        print triang.shape
        print fx.shape
        print Z.shape

        #plt.tricontourf(fx, fy, triang, Z)
        plt.triplot(fx, fy, triang)

        # now plot indices

        #plt.tricontourf(fx, fy, triang, Z)
        #plt.triplot(fx, fy, triang)
        #plt.colorbar()
        #plt.tricontour(fx, fy, triang, Z, colors='k')
        #tripcolor


        #full_mask = num.repeat(self.tri_full_flag == 1, 3)
        #ghost_mask = num.repeat(self.tri_full_flag == 0, 3)

        noe = self.domain.number_of_elements


        fx = vertices[:,0].reshape(noe,3)
        fy = vertices[:,1].reshape(noe,3)




        #-------------------------------------------
        # Neighbourhood Area
        #-------------------------------------------
        fx1 = fx[self.vols].flatten()
        fy1 = fy[self.vols].flatten()

        print 'fx1', fx1.shape

        print self.vols
        #gx = vertices[ghost_mask,0]
        #gy = vertices[ghost_mask,1]


        ## Plot full triangles
        n = int(len(fx1)/3)
        triang = num.array(range(0,3*n))
        triang.shape = (n, 3)
        print triang
        plt.triplot(fx1, fy1, triang, 'go-')



        self.vols
        #plt.plot()

        #-------------------------------------------
        # Update Area
        #-------------------------------------------
        fx0 = fx[self.indices].flatten()
        fy0 = fy[self.indices].flatten()

        print 'fx0', fx0.shape

        print self.indices
        #gx = vertices[ghost_mask,0]
        #gy = vertices[ghost_mask,1]


        ## Plot full triangles
        n = int(len(fx0)/3)
        triang = num.array(range(0,3*n))
        triang.shape = (n, 3)
        print triang
        plt.triplot(fx0, fy0, triang, 'bo-')


        #-------------------------------------------
        # Update Nodes
        #-------------------------------------------
        fx0 = fx[self.indices].flatten()
        fy0 = fy[self.indices].flatten()

        print 'fx0', fx0.shape

        print self.indices
        #gx = vertices[ghost_mask,0]
        #gy = vertices[ghost_mask,1]


        ## Plot full triangles
        n = int(len(fx0)/3)
        triang = num.array(range(0,3*n))
        triang.shape = (n, 3)
        print triang
        plt.triplot(fx0, fy0, triang, 'bo-')




        fx2 = fx[self.vol_ids,self.vert_ids]
        fy2 = fy[self.vol_ids,self.vert_ids]

        print 'fx2', fx2.shape

        plt.plot(fx2,fy2,'yo')

        #plt.tripcolor(fx,fy, triang, Z)
        
        ## Plot ghost triangles
        #n = int(len(gx)/3)
        #if n > 0:
            #triang = num.array(range(0,3*n))
            #triang.shape = (n, 3)
            #plt.triplot(gx, gy, triang, 'b--')

        # Save triangulation to location pointed by filename
        plt.savefig('dump.svg')

        plt.draw()
        plt.show()


    def setup_node_structures(self):
        """ For setting elevation we need to
        ensure that the elevation quantity remains
        continuous (at least for version 1.3 of anuga)

        So we need to find all the vertices that need to
        update within each timestep.
        """

        node_ids = set()

        for ind in self.indices:
            for k in [0,1,2]:
                node_ids.add(self.domain.triangles[ind,k])

        self.node_ids = [ id for id in node_ids ]


        self.node_index = self.domain.node_index

        vertex_ids =[]
        for nid in self.node_ids:
            #print nid,self.domain.number_of_triangles_per_node[nid]
            for vid in range(self.node_index[nid], self.node_index[nid+1]):
                vidd = self.domain.vertex_value_indices[vid]
                vertex_ids.append(vidd)
                #print '   ',nid, vid, vidd, vidd/3, vidd%3

        self.vol_ids  = num.array(vertex_ids,dtype=num.int)/3
        self.vols = num.array(list(set(self.vol_ids)), dtype=num.int)
        self.vert_ids = num.array(vertex_ids,dtype=num.int)%3





#===============================================================================
# Specific Erosion Operator for circular region.
#===============================================================================
class Circular_erosion_operator(Erosion_operator):
    """
    Erosion over a circular region

    """

    def __init__(self, domain,
                 threshold=0.0,
                 base=0.0,
                 center=None,
                 radius=None,
                 verbose=False):



        Erosion_operator.__init__(self,
                                  domain,
                                  threshold,
                                  base,
                                  center=center,
                                  radius=radius,
                                  verbose=verbose)





#===============================================================================
# Specific Bed Operators for polygonal region.
#===============================================================================
class Polygonal_erosion_operator(Erosion_operator):
    """
    Erosion over a ploygon

    """

    def __init__(self, domain,
                 threshold=0.0,
                 base=0.0,
                 polygon=None,
                 verbose=False):


        Erosion_operator.__init__(self,
                                  domain,
                                  threshold=threshold,
                                  base=base,
                                  polygon=polygon,
                                  verbose=verbose)







def lineno():
    """Returns the current line number in our program."""
    import inspect
    return inspect.currentframe().f_back.f_back.f_lineno



def stage_elev_info(self):
    print 80*"="

    print 'In Evolve: line number ', lineno()
    import inspect
    print inspect.getfile(lineno)

    print 80*"="
    ind = num.array([ 976,  977,  978,  979,  980,  981,  982,  983, 1016, 1017, 1018,
             1019, 1020, 1021, 1022, 1023])
    elev_v = self.get_quantity('elevation').vertex_values
    stage_v = self.get_quantity('stage').vertex_values
    elev_c = self.get_quantity('elevation').centroid_values
    stage_c = self.get_quantity('stage').centroid_values

    from pprint import pprint
    print 'elev_v, elev_c, elev_avg \n'
    pprint( num.concatenate( (elev_v[ind], (elev_c[ind]).reshape(16,1),
                               num.mean(elev_v[ind],axis=1).reshape(16,1)), axis = 1))
    print 'stage_v, stage_c, stage_avg \n'
    pprint( num.concatenate( (stage_v[ind], (stage_c[ind]).reshape(16,1),
                               num.mean(stage_v[ind],axis=1).reshape(16,1)), axis = 1))

    print 80*"="
